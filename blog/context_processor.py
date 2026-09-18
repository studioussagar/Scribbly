from blog.models import Category,Notification

def categories_processor(request):
    return {'categories': Category.objects.all()}


def notification_count(request):

    if request.user.is_authenticated:

        notifications = Notification.objects.filter(
            recipient=request.user
        ).order_by("-created_at")

        return {
            "unread_notifications": notifications.filter(
                is_read=False
            ).count(),

            "recent_notifications": notifications[:5]
        }

    return {
        "unread_notifications": 0,
        "recent_notifications": []
    }