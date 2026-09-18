from django.shortcuts import get_object_or_404, redirect, render
from django.views import generic
from django.db.models import Count, Sum
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse, reverse_lazy
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from django.db.models import Count
from ..models import Comment, Like, Follow
from PIL import Image
from django.contrib.auth import get_user_model
from ..forms import CustomUserForm, ProfileForm 
User = get_user_model()


def build_profile_context(user_obj):
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
        if self.request.user.is_authenticated:
            ctx['is_following'] = Follow.objects.filter(
                follower=self.request.user,
                following=self.object
        ).exists()
        else:
            ctx['is_following'] = False
        ctx['followers_count'] = Follow.objects.filter(following=self.object).count()

        ctx['following_count'] = Follow.objects.filter(follower=self.object).count()
        
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
