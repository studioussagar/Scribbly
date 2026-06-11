from django.shortcuts import get_object_or_404, redirect,render
from django.views import generic
from django.db.models import Count, Sum
from django.contrib import messages
from django.contrib.auth import login,get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin,UserPassesTestMixin
from django.contrib.auth.views import LogoutView
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy,reverse
from django import forms
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseRedirect
from django.db.models import Count,Q
from .models import *
from .forms import BlogCreateForm,MessageForm,CustomUserForm,ProfileForm,CustomSignupForm
from .decorators import login_required_no_redirect
from .utils import sanitize_html
from django_ratelimit.decorators import ratelimit
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator
from PIL import Image

# -------------------------------
# Blog Display Views
# -------------------------------

class BlogHome(generic.ListView):
    template_name = 'home.html'
    queryset = Post.objects.filter(status=1).order_by('-date_created')[:5]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['featured_post'] = Post.objects.filter(status=1).order_by('-date_created').first()
        context['popular_posts'] = Post.objects.filter(status=1).order_by('-date_created')[:3]
        return context

class BlogList(generic.ListView):
    template_name = "blog_list.html"
    context_object_name = "posts"
    paginate_by = 10

    def get_queryset(self):
        qs = (
            Post.objects.filter(status=1)
            .select_related("author")
            .prefetch_related("category")
            .order_by("-date_created")
        )
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(title__icontains=q)
                | Q(content__icontains=q)
                | Q(author__name__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = Category.objects.all()
        ctx["query"] = self.request.GET.get("q", "").strip()
        return ctx

class BlogView(generic.DetailView):
    model = Post
    template_name = 'blog.html'
    def get_queryset(self):
        return Post.objects.filter(status=1)

class BlogAbout(generic.TemplateView):
    template_name = 'about.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tech_stack'] = [
            "Django", "Python", "Bootstrap 5", "JavaScript",
            "WebSockets (Channels)", "TinyMCE", "SQLite", "HTML & CSS"
        ]
        return context

# -------------------------------
# Authentication Views
# -------------------------------
@method_decorator(csrf_protect, name='dispatch')
@method_decorator(ratelimit(key='ip', rate='5/5m', method='POST'), name='dispatch')
class BlogSignup(generic.FormView):
    template_name = 'login_signup.html'
    form_class = CustomSignupForm  # your updated form with password validation
    success_url = reverse_lazy('home_view')

    def form_valid(self, form):
        user = form.save()
        from .utils import send_verification_email
        send_verification_email(self.request, user)
        messages.success(self.request, f"Welcome, {user.name}! Please check your email to verify and activate your account.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Signup failed. Please check the form.")
        print("Signup form errors:", form.errors)
        return super().form_invalid(form)

@method_decorator(csrf_protect, name='dispatch')
@method_decorator(ratelimit(key='ip', rate='10/5m', method='POST'), name='dispatch')
class BlogLogin(generic.FormView):
    template_name = 'login_signup.html'
    form_class = AuthenticationForm
    success_url = reverse_lazy('home_view')

    def form_valid(self, form):
        user = form.get_user()
        login(self.request, user)
        messages.success(self.request, f"Welcome back, {user.name}!")
        return super().form_valid(form)

class BlogLogout(LogoutView):
    next_page = reverse_lazy('home_view')

    def post(self, request, *args, **kwargs):
        messages.success(request, "You have been successfully logged out.")
        return super().post(request, *args, **kwargs)

class CustomPasswordChangeView(PasswordChangeView):
    template_name = 'password_change.html'
    
    def get_success_url(self):
        messages.success(self.request, "Your password was changed successfully!")
        return reverse_lazy('profiles:profile_me')

class ActivateAccountView(generic.View):
    def get(self, request, uidb64, token, *args, **kwargs):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = get_user_model().objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            messages.success(request, 'Thank you for confirming your email. You can now log in to your account.')
            return redirect('login')
        else:
            messages.error(request, 'Activation link is invalid or has expired!')
            return redirect('login')


# -------------------------------
# Blog Creation Views
# -------------------------------
@method_decorator(csrf_protect, name='dispatch')
class BlogCreate(LoginRequiredMixin, generic.CreateView):
    model = Post
    form_class = BlogCreateForm
    template_name = 'create_blog.html'
    success_url = reverse_lazy('home_view')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['author'] = self.request.user
        return kwargs

    def form_valid(self, form):
        user = self.request.user
        form.instance.author = user
        form.instance.content = sanitize_html(form.cleaned_data.get('content', ''))
        if user.is_author:
            form.instance.status = form.cleaned_data.get('status')
        else:
            form.instance.status = 2
        messages.success(self.request, "Your blog has been published successfully!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context

@method_decorator(csrf_protect, name='dispatch')
class ViewerBlogTry(LoginRequiredMixin, generic.CreateView):
    model = Post
    form_class = BlogCreateForm
    template_name = 'create_blog.html'
    success_url = reverse_lazy('home_view')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['author'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.content = sanitize_html(form.cleaned_data.get('content', ''))
        form.instance.status = 2  # pending review
        messages.success(
            self.request,
            "Your blog has been submitted for review! If it resonates, you'll be invited to become an Author."
        )
        return super().form_valid(form)

    def form_invalid(self, form):
        print(form.errors)
        return super().form_invalid(form)

    def dispatch(self, request, *args, **kwargs):
        # Guard: is_author raises AttributeError on AnonymousUser — check auth first
        if request.user.is_authenticated and request.user.is_author:
            return redirect('create_blog')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context

class BlogCategory(generic.ListView):
    model = Post
    template_name = 'category_post.html'
    paginate_by = 10

    def get_queryset(self):
        slug = self.kwargs.get('slug')
        category = Category.objects.filter(slug=slug).first()
        if category:
            return Post.objects.filter(category=category, status=1).order_by('-date_created')
        return Post.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = Category.objects.filter(slug=self.kwargs.get('slug')).first()
        return context

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

# -------------------------------
# Functional Post Interaction Views
# -------------------------------
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
    else:
        liked = True
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

class PostEditView(LoginRequiredMixin, UserPassesTestMixin, generic.edit.UpdateView):
    model = Post
    form_class = BlogCreateForm
    template_name = 'create_blog.html'
    success_url = reverse_lazy('dashboard')

    def get_object(self, queryset=None):
        return get_object_or_404(Post, slug=self.kwargs['slug'], author=self.request.user)

    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['author'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.content = sanitize_html(form.cleaned_data.get('content', ''))
        messages.success(self.request, "Post updated successfully!")
        return super().form_valid(form)

@csrf_protect
@login_required
@require_POST
def delete_post_dashboard(request, slug):
    post = get_object_or_404(Post, slug=slug, author=request.user)
    post.delete()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'Post deleted'})
    return redirect('dashboard')

User = get_user_model()

def build_profile_context(user_obj):
    from django.utils import timezone
    posts_qs = user_obj.posts.all().select_related("author", "category")
    aggregates = posts_qs.annotate(
        _lc=Count("likes", distinct=True), _dc=Count("dislikes", distinct=True)
    ).aggregate(
        aggregate_likes=Sum("_lc"),
        aggregate_dislikes=Sum("_dc"),
    )

    # Build a real chronological activity feed
    activity = []
    for post in user_obj.posts.filter(status=1).order_by('-date_created')[:5]:
        activity.append({
            'text': f'Published <a href="/{post.slug}/">{post.title}</a>',
            'when': post.date_created,
            'private': False,
        })
    for comment in Comment.objects.filter(user=user_obj).order_by('-date_created')[:5]:
        activity.append({
            'text': f'Commented on <a href="/{comment.post.slug}/">{comment.post.title}</a>',
            'when': comment.date_created,
            'private': False,
        })
    for like in Like.objects.filter(user=user_obj).order_by('-id')[:5]:
        activity.append({
            'text': f'Liked <a href="/{like.post.slug}/">{like.post.title}</a>',
            'when': like.post.date_created,
            'private': True,
        })
    # Sort by most recent first
    activity.sort(key=lambda x: x['when'], reverse=True)
    recent_activity = activity[:10]

    return {
        "profile_user": user_obj,
        "aggregate": {k: (v or 0) for k, v in aggregates.items()},
        "recent_activity": recent_activity,
    }

class ProfileMeRedirectView(LoginRequiredMixin, generic.RedirectView):
    permanent = False
    def get_redirect_url(self, *args, **kwargs):
        return reverse("profiles:profile_detail", kwargs={"username": self.request.user.username})

class ProfileDetailView(generic.DetailView):
    template_name = "profile.html"
    context_object_name = "profile_user"

    def get_object(self, queryset=None):
        return get_object_or_404(User.objects.select_related("profile"), username=self.kwargs["username"])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(build_profile_context(self.object))
        ctx['filtered_posts'] = self.object.posts.filter(status=0)[:5]
        ctx['posts'] = self.object.posts.filter(status=1)[:10]
        
        return ctx

@method_decorator(csrf_protect, name='dispatch')
class AvatarUploadView(LoginRequiredMixin, generic.View):
    def post(self, request, *args, **kwargs):
        f = request.FILES.get("avatar")

        if not f:
            messages.error(request, "Please select an image.")
            return redirect(
                "profiles:profile_detail",
                username=request.user.username
            )

        # Allowed image MIME types
        allowed_types = {
            "image/jpeg",
            "image/png",
            "image/webp",
            "image/gif",
        }

        if f.content_type not in allowed_types:
            messages.error(
                request,
                "Only JPG, PNG, WEBP, and GIF images are allowed."
            )
            return redirect(
                "profiles:profile_detail",
                username=request.user.username
            )

        # Maximum file size: 5 MB
        if f.size > 5 * 1024 * 1024:
            messages.error(
                request,
                "Image size must be less than 5 MB."
            )
            return redirect(
                "profiles:profile_detail",
                username=request.user.username
            )

        # Verify that the uploaded file is actually an image
        try:
            img = Image.open(f)
            img.verify()
            f.seek(0)  # Reset file pointer after verification
        except Exception:
            messages.error(request, "Invalid image file.")
            return redirect(
                "profiles:profile_detail",
                username=request.user.username
            )

        prof = request.user.profile
        prof.avatar = f
        prof.avatar_url_override = None
        prof.save()

        messages.success(request, "Avatar updated successfully.")

        return redirect(
            "profiles:profile_detail",
            username=request.user.username
        )

@method_decorator(csrf_protect, name='dispatch')
class DefaultAvatarSetView(LoginRequiredMixin, generic.View):
    def post(self, request, *args, **kwargs):
        src = request.POST.get("src")
        if not src:
            return JsonResponse({"ok": False, "error": "no_src"}, status=400)
        prof = request.user.profile
        prof.avatar = None
        prof.avatar_url_override = src
        prof.save()
        return JsonResponse({"ok": True})

@method_decorator(csrf_protect, name='dispatch')
class FollowToggleView(LoginRequiredMixin, UserPassesTestMixin, generic.View):

    def test_func(self):
        target_username = self.kwargs["username"]
        return self.request.user.username != target_username

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return HttpResponseForbidden("Cannot follow yourself.")
        return super().handle_no_permission()

    def post(self, request, *args, **kwargs):
        target = get_object_or_404(User, username=self.kwargs["username"])
        follower = request.user

        # Check if Follow already exists
        follow_qs = Follow.objects.filter(follower=follower, following=target)
        if follow_qs.exists():
            # Unfollow user
            follow_qs.delete()
            state = "unfollowed"
        else:
            # Create follow record
            Follow.objects.create(follower=follower, following=target)
            state = "followed"

        return JsonResponse({"ok": True, "state": state})
    
@method_decorator(csrf_protect, name='dispatch')
class InboxView(LoginRequiredMixin, generic.TemplateView):
    template_name = 'inbox.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx['conversations'] = Conversation.objects.filter(
            Q(user1=user) | Q(user2=user)
        ).select_related('user1', 'user2').prefetch_related('messages').order_by('-updated_at')
        return ctx

@method_decorator(csrf_protect, name='dispatch')
class MessageUserView(LoginRequiredMixin, generic.FormView):
    form_class = MessageForm
    template_name = 'message.html' 

    def dispatch(self, request, *args, **kwargs):
        self.target_user = get_object_or_404(User, username=kwargs['target_username'])
        users = sorted([request.user, self.target_user], key=lambda u: u.id)
        convo, _ = Conversation.objects.get_or_create(user1=users[0], user2=users[1])
        self.conversation = convo
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('ajax') == '1':
            last_id = request.GET.get('last_id', 0)
            try:
                last_id = int(last_id)
            except ValueError:
                last_id = 0
                
            from django.utils import timezone
            new_msgs = self.conversation.messages.filter(id__gt=last_id).order_by('created_at')
            data = []
            for m in new_msgs:
                local_dt = timezone.localtime(m.created_at)
                data.append({
                    'id': m.id,
                    'text': m.text,
                    'sender': m.sender.username,
                    'created_at': local_dt.strftime('%H:%M')
                })
            return JsonResponse({'messages': data})
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **ctx):
        ctx = super().get_context_data(**ctx)
        user = self.request.user
        ctx['conversations'] = Conversation.objects.filter(
            Q(user1=user) | Q(user2=user)
        ).select_related('user1', 'user2').prefetch_related('messages').order_by('-updated_at')
        ctx['conversation'] = self.conversation
        ctx['messages'] = self.conversation.messages.order_by('created_at')
        ctx['other_user'] = self.target_user
        return ctx

    def form_valid(self, form):
        msg = form.save(commit=False)
        msg.conversation = self.conversation
        msg.sender = self.request.user
        msg.save()
        
        # Ensure created_at is populated and synchronized
        msg.refresh_from_db()
        
        # Touch the conversation to update ordering
        self.conversation.updated_at = msg.created_at
        self.conversation.save(update_fields=['updated_at'])
        
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest' or self.request.GET.get('ajax') == '1':
            from django.utils import timezone
            local_dt = timezone.localtime(msg.created_at)
            return JsonResponse({
                'ok': True,
                'msg': {
                    'id': msg.id,
                    'text': msg.text,
                    'sender': msg.sender.username,
                    'created_at': local_dt.strftime('%H:%M')
                }
            })
            
        return redirect('profiles:message_user', target_username=self.kwargs['target_username'])

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'error': form.errors})
        return super().form_invalid(form)
    
@csrf_protect
@login_required
@require_POST
def mark_read(request, pk):
    convo = get_object_or_404(Conversation, pk=pk)
    if request.user not in convo.participants():
        return JsonResponse({"error": "forbidden"}, status=403)
    Message.objects.filter(conversation=convo, is_read=False).exclude(sender=request.user).update(is_read=True)
    return JsonResponse({"ok": True})

class ProfileEditView(LoginRequiredMixin, generic.View):
    template_name = 'edit_profile.html'
    success_url = reverse_lazy('profiles:profile_me')

    def get(self, request, *args, **kwargs):
        user_form = CustomUserForm(instance=request.user)
        profile_form = ProfileForm(instance=request.user.profile)
        return render(request, self.template_name, {
            'user_form': user_form,
            'profile_form': profile_form,
        })

    def post(self, request, *args, **kwargs):
        user_form = CustomUserForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            return redirect(self.success_url)

        return render(request, self.template_name, {
            'user_form': user_form,
            'profile_form': profile_form,
        })

def custom_404(request, exception):
    return render(request, '404.html', status=404)

def custom_500(request):
    return render(request, '500.html', status=500)