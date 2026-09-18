from review_center.models import ReviewAction, AgentDecision
from blog.utils import create_notification
from django.urls import reverse

class ApproveEngine:
    def __init__(self, application):
        self.application = application

    def accept(self):
        user = self.application.user
        self.application.status = "approved"
        user.approved_for_author = True
        self.application.save()
        user.save()

        ReviewAction.objects.create(
                    application=self.application,
                    action="approved",
                    reviewer=None
                )

        create_notification(
                    recipient=user,
                    actor=None,
                    notification_type="system",
                    text = f"Your application has been approved. You can now start writing blogs.",
                    link = reverse("dashboard")
        
                )
    