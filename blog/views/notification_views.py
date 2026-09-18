from ..models import Notification
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin

class NotificationListView(generic.ListView,LoginRequiredMixin):
    template_name = 'notifications.html'
    context_object_name = 'notifications'

    def get_queryset(self):
        Notification.objects.filter(recipient=self.request.user, is_read = False).update(is_read=True)
        return Notification.objects.filter(recipient=self.request.user).order_by('-created_at')