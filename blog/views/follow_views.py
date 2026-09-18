from django.shortcuts import get_object_or_404
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.http import JsonResponse, HttpResponseForbidden
from ..models import Follow,Notification
from ..utils import create_notification
from django.contrib.auth import get_user_model
from django.urls import reverse
User = get_user_model()


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

        target = get_object_or_404(
        User,
        username=self.kwargs["username"]
    )

        follower = request.user

        follow_qs = Follow.objects.filter(
            follower=follower,
            following=target
    )

        if follow_qs.exists():
            follow_qs.delete()
            Notification.objects.filter(
            recipient=target,
            actor=follower,
            notification_type="follow",
            is_read=False
        ).delete()

            state = "unfollowed"

        else:
            Follow.objects.create(
            follower=follower,
            following=target
        )
            create_notification(
            recipient=target,
            actor=follower,
            notification_type="follow",
            text=f"{follower.username} started following you.",
            link=reverse(
                "profiles:profile_detail",
                kwargs={
                    "username": follower.username
                }
            )
        )
            state = "followed"
        return JsonResponse({
        "ok": True,
        "state": state
    })

class FollowersListView(LoginRequiredMixin, generic.ListView):
    template_name = "followers_list.html"
    context_object_name = "followers"

    def get_queryset(self):
        profile_user = get_object_or_404(
            User,
            username=self.kwargs["username"]
        )

        return (
            Follow.objects
            .filter(following=profile_user)
            .select_related("follower")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["profile_user"] = get_object_or_404(
            User,
            username=self.kwargs["username"]
        )
        return ctx

class FollowingListView(LoginRequiredMixin, generic.ListView):
    template_name = "following_list.html"
    context_object_name = "following"

    def get_queryset(self):
        profile_user = get_object_or_404(
            User,
            username=self.kwargs["username"]
        )

        return (
            Follow.objects
            .filter(follower=profile_user)
            .select_related("following")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["profile_user"] = get_object_or_404(
            User,
            username=self.kwargs["username"]
        )
        return ctx