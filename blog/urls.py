from . import views
from django.urls import path,include

urlpatterns = [
    path('', views.BlogHome.as_view(), name='home_view'),                            # Homepage
    path('create/', views.BlogCreate.as_view(), name='create_blog'),
     path('profiles/', include('blog.profile_urls', namespace='profiles')),
    path('try/', views.ViewerBlogTry.as_view(), name='try_blog'),
    path('blog-list/', views.BlogList.as_view(), name='blog_list'),                  # Full blog list
    path('login/', views.BlogLogin.as_view(), name='login'),
    path('signup/', views.BlogSignup.as_view(), name='signup'),                      # Signup view
    path('activate/<uidb64>/<token>/', views.ActivateAccountView.as_view(), name='activate'),
    path('logout/', views.BlogLogout.as_view(), name='logout'),
    path('password-change/', views.CustomPasswordChangeView.as_view(), name='password_change'),
    path('about/', views.BlogAbout.as_view(), name='about_view'),                    # About page
    path('category/<slug:slug>/', views.BlogCategory.as_view(), name='category_posts'),  # Posts by category
    path('like/<slug:slug>/', views.like_post, name='like_post'),
    path('dislike/<slug:slug>/', views.dislike_post, name='dislike_post'),           # Dislike post toggle
    path('liked-posts/', views.BlogLike.as_view(), name='liked_posts'),              # Posts liked by user
    path('disliked-posts/', views.BlogDislike.as_view(), name='disliked_posts'),     # Posts disliked by user
    path('add-comment/<slug:slug>', views.add_comment, name='add_comment'),
    path('share-post/<slug:slug>/', views.share_post, name='share_post'),
    path('shared-posts/', views.BlogShare.as_view(), name='shared_posts'),           # Posts shared by user
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),             # User Dashboard
    path('edit/<slug:slug>/', views.PostEditView.as_view(), name='edit_post'),
    path('dashboard/delete/<slug:slug>/', views.delete_post_dashboard, name='delete_post'),
   
    path('<slug:slug>/', views.BlogView.as_view(), name='blog_view'),                # Detail view for a blog post
]
