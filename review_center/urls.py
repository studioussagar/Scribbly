from django.urls import path

from .views import ReviewDashboardView,PendingApplicationsView, ApplicationReviewDetailView, ApproveApplicationView,RejectApplicationView, AnalyzeApplicationView

app_name = "review_center"

urlpatterns = [
    path( "", ReviewDashboardView.as_view(), name="dashboard" ),
    path("pending/", PendingApplicationsView.as_view(), name="pending" ),
    path("application/<int:pk>/", ApplicationReviewDetailView.as_view(),name="application-detail"),
    path("application/<int:pk>/approve/", ApproveApplicationView.as_view(), name="approve"),
    path("application/<int:pk>/reject/",RejectApplicationView.as_view(),name="reject"),
    path( "application/<int:pk>/analyze/", AnalyzeApplicationView.as_view(), name="analyze-application"),
]