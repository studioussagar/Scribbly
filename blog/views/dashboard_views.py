from django.shortcuts import get_object_or_404, redirect
from django.views import generic
from django.db.models import Count
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from django.db.models import Count
from ..models import Post, Comment, Category



class DashboardView(LoginRequiredMixin, generic.TemplateView):
    template_name = 'dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        if user.is_author:
            context['user_posts'] = Post.objects.filter(author=user).annotate(
                total_likes=Count('likes'),
                total_dislikes=Count('dislikes'),
            ).order_by('-date_created')

            context['recent_comments'] = Comment.objects.filter(
                post__author=user
            ).order_by('-date_created')[:5]

        else:
            liked_categories = Category.objects.filter(posts__likes__user=user).distinct()

            context['recommended_posts'] = Post.objects.filter(
                category__in=liked_categories,
                status=1
            ).exclude(author=user).distinct().order_by('-date_created')[:10]

            context['user_can_become_author'] = (user.role == 'viewer' and user.approved_for_author)

        return context

    @method_decorator(csrf_protect)
    def post(self, request, *args, **kwargs):
        user = request.user
        action = request.POST.get('action')

        if action == 'become_author' and user.role == 'viewer' and user.approved_for_author:
            user.role = 'author'
            user.approved_for_author = False
            user.save()
            messages.success(self.request, "Congratulations! You are now an author.")
            return redirect('dashboard')

        return redirect('dashboard')


@csrf_protect
@login_required
@require_POST
def delete_post_dashboard(request, slug):
    post = get_object_or_404(Post, slug=slug, author=request.user)
    post.delete()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'Post deleted'})
    return redirect('dashboard')
