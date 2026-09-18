from django.shortcuts import get_object_or_404, redirect
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.http import JsonResponse
from ..models import Post, Like, Dislike, Comment, Share, Notification
from ..decorators import login_required_no_redirect
from ..utils import sanitize_html, create_notification


# -------------------------------
# Functional Post Interaction Views
# -------------------------------


class BlogLike(LoginRequiredMixin, generic.ListView):
    model = Post
    template_name = 'liked_post.html'
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        return Post.objects.filter(likes__user=user, status=1).order_by('-date_created')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['type'] = 'Liked'
        return context

class BlogShare(LoginRequiredMixin, generic.ListView):
    model = Post
    template_name = 'shared_post.html'
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        return Post.objects.filter(shares__user=user, status=1).order_by('-date_created')

@csrf_protect
@login_required_no_redirect
@require_POST
def share_post(request, slug):
    post = get_object_or_404(Post, slug=slug, status = 1)
    Share.objects.get_or_create(user=request.user, post=post)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'Shared successfully'})
    return redirect(post.get_absolute_url())

@csrf_protect
@login_required_no_redirect
@require_POST
def like_post(request, slug):
    post = get_object_or_404(Post, slug=slug, status = 1)
    user = request.user
    Dislike.objects.filter(post=post, user=user).delete()
    like_obj, created = Like.objects.get_or_create(user=user, post=post)
    if not created:
        like_obj.delete()
        liked = False
        Notification.objects.filter(
            recipient=post.author,
            actor=user,
            notification_type="like",
            is_read=False
        ).delete()
    else:
        liked = True
        if post.author != user:
                create_notification(
                recipient=post.author,
                actor=user,
                notification_type="like",
                text=f"{user.username} liked your post '{post.title}'.",
                link=post.get_absolute_url()
            )
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'liked': liked,
            'total_likes': post.likes.count(),
            'total_dislikes': post.dislikes.count(),
        })
    return redirect(post.get_absolute_url())

from django.utils import timezone

@csrf_protect
@login_required_no_redirect
@require_POST
def add_comment(request, slug):
    post = get_object_or_404(Post, slug=slug, status = 1)
    content = request.POST.get('content')
    parent_id = request.POST.get('parent_id')
    if content:
        content = sanitize_html(content, strip_all=True)
        parent = None
        if parent_id:
            parent = get_object_or_404(Comment, id=parent_id, post=post)
        comment = Comment.objects.create(user=request.user, post=post, content=content, parent=parent)
        if post.author != request.user:
            create_notification(
                recipient=post.author,
                actor=request.user,
                notification_type="comment",
                text=f"{request.user.username} commented on '{post.title}'.",
                link=post.get_absolute_url()
            )
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'comment_id': comment.id,
                'comment_author': request.user.name,
                'comment_date': timezone.now().strftime('%b %d, %Y'),
                'comment_content': content,
                'parent_id': parent_id,
            })
    return redirect(post.get_absolute_url())

class BlogComment(generic.ListView):
    model = Post
    template_name = 'blog_comments.html'
    context_object_name = 'posts_with_comments'
    paginate_by = 10

    def get_queryset(self):
        return Post.objects.filter(comments__isnull=False, status=1).distinct().order_by('-date_created')

@csrf_protect
@login_required
@require_POST
def dislike_post(request, slug):
    post = get_object_or_404(Post, slug=slug, status = 1)
    user = request.user
    Like.objects.filter(post=post, user=user).delete()
    dislike_obj, created = Dislike.objects.get_or_create(user=user, post=post)
    if not created:
        dislike_obj.delete()
        disliked = False
    else:
        disliked = True
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'disliked': disliked,
            'total_dislikes': post.dislikes.count(),
            'total_likes': post.likes.count(),
        })
    return redirect(post.get_absolute_url())

class BlogDislike(LoginRequiredMixin,generic.ListView):
    model = Post
    template_name = 'liked_post.html'
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        return Post.objects.filter(dislikes__user=user, status=1).order_by('-date_created')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['type'] = 'Disliked'
        return context
