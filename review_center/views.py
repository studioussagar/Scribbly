from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.views import View
from django.core.exceptions import PermissionDenied
from review_center.models import WriterApplication, ApplicationAnalysis, RiskAssessment, AgentDecision, ReviewAction
from review_center.services.talent_acquisition.orchestrator import TalentAcquisitionOrchestrate
from blog.utils import create_notification
from django.urls import reverse

class StaffRequiredMixin(UserPassesTestMixin, LoginRequiredMixin):
    def test_func(self):
        return self.request.user.is_staff

    def handle_no_permission(self):
        raise PermissionDenied("You do not have permission to access this page.")



class ReviewDashboardView(TemplateView, StaffRequiredMixin):
    template_name = "review_center/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        ctx["pending_count"] = (
            WriterApplication.objects.filter(
                status="pending"
            ).count()
        )

        ctx["approved_count"] = (
            WriterApplication.objects.filter(
                status="approved"
            ).count()
        )

        ctx["rejected_count"] = (
            WriterApplication.objects.filter(
                status="rejected"
            ).count()
        )

        ctx["escalated_count"] = (
            WriterApplication.objects.filter(
                status="escalated"
            ).count()
        )

        ctx["recent_applications"] = (
            WriterApplication.objects
            .select_related("user")
            .order_by("-submitted_at")[:10]
        )

        return ctx

class PendingApplicationsView(StaffRequiredMixin, ListView):
    model = WriterApplication
    template_name = "review_center/pending.html"
    context_object_name = "applications"
    paginate_by = 20

    def get_queryset(self):
        return (
            WriterApplication.objects.select_related("user","preview_blog").filter(status="pending").order_by("-submitted_at")
    )


class ApplicationReviewDetailView(StaffRequiredMixin,DetailView):
    model = WriterApplication
    template_name = "review_center/application_detail.html"
    context_object_name = "application"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        application = self.object

        ctx["blog"] = application.preview_blog

        ctx["analysis"] = getattr(application, "applicationanalysis", None )

        ctx["risk"] = getattr( application, "riskassessment", None )

        ctx["decision"] = getattr(application, "agentdecision", None )

        return ctx


class ApproveApplicationView( StaffRequiredMixin, View):
    def post(self,request,pk):
        application = get_object_or_404(WriterApplication, pk=pk, status="pending")
        user = application.user
        application.status = "approved"
        user.approved_for_author = True
        application.save()
        user.save()

        ReviewAction.objects.create(
            application=application,
            action="approved",
            reviewer=request.user
        )

        create_notification(
            recipient=user,
            actor=request.user,
            notification_type="system",
            text = f"Your application has been approved. You can now start writing blogs.",
            link = reverse("dashboard")

        )
        
        messages.success(request, "Application approved successfully.")
        return redirect("review_center:application-detail", pk=pk)


class RejectApplicationView(StaffRequiredMixin, View):
    def post(self, request, pk):
        application = get_object_or_404(WriterApplication, pk=pk, status="pending")
        applicant = application.user
        application.status = "rejected"
        applicant.approved_for_author = False
        application.save()
        applicant.save()

        ReviewAction.objects.create(
            application=application,
            action="rejected",
            reviewer=request.user
        )

        create_notification(
            recipient=applicant,
            actor=request.user,
            notification_type="system",
            text = f"Your application has been rejected. You can reapply after addressing the feedback.",
            link = reverse("dashboard")
        )

        messages.success(request, "Application rejected successfully.")
        return redirect("review_center:application-detail", pk=pk)


class AnalyzeApplicationView(StaffRequiredMixin, View):

    def post(self, request, pk):
        application = get_object_or_404( WriterApplication, pk=pk )
        TalentAcquisitionOrchestrate().process(application)
        messages.success(request,"Application analyzed successfully.")
        return redirect("review_center:application-detail", pk=pk )

