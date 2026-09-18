from review_center.models import ReviewAction, AgentDecision
from blog.utils import create_notification
from django.urls import reverse


class RejectEngine:
    def __init__(self, application):
        self.application = application

    def reject(self):
        user = self.application.user
        self.application.status = "rejected"
        user.approved_for_author = False
        self.application.save()
        user.save()

        ReviewAction.objects.create(
                    application=self.application,
                    action="rejected",
                    reviewer=None
                )

        create_notification(
                    recipient=user,
                    actor=None,
                    notification_type="system",
                    text = f"Your application has been rejected. You can reapply after addressing the feedback.",
                    link = reverse("dashboard")
        
                )