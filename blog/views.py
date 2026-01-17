from django.shortcuts import get_object_or_404, redirect,render
from django.views import generic
from django.db.models import Count, Sum
from django.contrib import messages
from django.contrib.auth import login,get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin,UserPassesTestMixin
from django.contrib.auth.views import LogoutView
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

class BlogAbout(generic.TemplateView):
    template_name = 'about.html'

# -------------------------------
# Authentication Views
# -------------------------------
@method_decorator(csrf_protect, name='dispatch')
class BlogSignup(generic.FormView):
    template_name = 'login_signup.html'
    form_class = CustomSignupForm  # your updated form with password validation
    success_url = reverse_lazy('home_view')

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(self.request, f"Welcome, {user.name}! Your account has been created.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Signup failed. Please check the form.")
        print("Signup form errors:", form.errors)
        return super().form_invalid(form)

@method_decorator(csrf_protect, name='dispatch')
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
        if user.is_author:
            form.instance.status = form.cleaned_data.get('status')
        else:
            form.instance.status = 2
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
        form.instance.status = 2
        return super().form_valid(form)

    def form_invalid(self, form):
        print(form.errors)
        return super().form_invalid(form)

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_author:
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

class BlogLike(generic.ListView):
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

class BlogShare(generic.ListView):
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
@login_required
@require_POST
def share_post(request, slug):
    post = get_object_or_404(Post, slug=slug)
    Share.objects.get_or_create(user=request.user, post=post)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'Shared successfully'})
    return redirect(post.get_absolute_url())

@csrf_protect
@login_required
@require_POST
def like_post(request, slug):
    post = get_object_or_404(Post, slug=slug)
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
@login_required
@require_POST
def add_comment(request, slug):
    post = get_object_or_404(Post, slug=slug)
    content = request.POST.get('content')
    if content:
        comment = Comment.objects.create(user=request.user, post=post, content=content)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'comment_author': request.user.name,
                'comment_date': timezone.now().strftime('%b %d, %Y'),
                'comment_content': content,
            })
    return redirect(post.get_absolute_url())

class BlogComment(generic.ListView):
    model = Post
    template_name = 'blog_comments.html'
    context_object_name = 'posts_with_comments'
    paginate_by = 10

    def get_queryset(self):
        return Post.objects.filter(comments__isnull=False).distinct().order_by('-date_created')

@csrf_protect
@login_required
@require_POST
def dislike_post(request, slug):
    post = get_object_or_404(Post, slug=slug)
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

class BlogDislike(generic.ListView):
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
    posts_qs = user_obj.posts.all().select_related("author", "category")
    aggregates = posts_qs.annotate(
        _lc=Count("likes"), _dc=Count("dislikes")
    ).aggregate(
        aggregate_likes=Sum("_lc"),
        aggregate_dislikes=Sum("_dc"),
    )
    recent_activity = getattr(user_obj.profile, "recent_activity", [])
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
            return redirect("blog:profile_detail", username=request.user.username)
        prof = request.user.profile
        prof.avatar = f
        prof.avatar_url_override = None
        prof.save()
        return redirect("blog:profile_detail", username=request.user.username)

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
class MessageUserView(LoginRequiredMixin, generic.FormView):
    form_class = MessageForm
    template_name = 'message.html' # changed from 'blog/message.html'

    def dispatch(self, request, *args, **kwargs):
        other = get_object_or_404(User, username=kwargs['target_username'])
        users = sorted([request.user, other], key=lambda u: u.id)
        convo, _ = Conversation.objects.get_or_create(user1=users[0], user2=users[1])
        self.conversation = convo
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **ctx):
        ctx = super().get_context_data(**ctx)
        ctx['conversation'] = self.conversation
        ctx['messages'] = self.conversation.messages.order_by('created_at')
        ctx['other_user'] = self.kwargs['target_username']
        return ctx

    def form_valid(self, form):
        msg = form.save(commit=False)
        msg.conversation = self.conversation
        msg.sender = self.request.user
        msg.save()
        return redirect('profiles:message_user',target_username=self.kwargs['target_username'])
    
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