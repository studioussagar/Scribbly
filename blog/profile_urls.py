# blog/profile_urls.py
from django.urls import path
from . import views

app_name = "profiles"

urlpatterns = [
    path("@/me/", views.ProfileMeRedirectView.as_view(), name="profile_me"),
    path("@/<str:username>/", views.ProfileDetailView.as_view(), name="profile_detail"),
    path("@/avatar/upload/", views.AvatarUploadView.as_view(), name="upload_avatar"),
    path("@/avatar/default/", views.DefaultAvatarSetView.as_view(), name="set_default_avatar"),
    path('edit/', views.ProfileEditView.as_view(), name='edit_profile'),
    # optional
    path("@/follow/<str:username>/", views.FollowToggleView.as_view(), name="toggle_follow"),
    path("inbox/", views.InboxView.as_view(), name="inbox"),
    path('notifications/',views.NotificationListView.as_view(), name='notifications'),  # Notifications view

    path("@/message/<str:target_username>/", views.MessageUserView.as_view(), name="message_user"),
    path( "<str:username>/followers/", views.FollowersListView.as_view(), name="followers"),
    path( "<str:username>/following/", views.FollowingListView.as_view(), name="following"),

]
