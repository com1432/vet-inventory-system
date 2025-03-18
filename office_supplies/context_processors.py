from .models import Notification

def notifications(request):
    if request.user.is_authenticated:
        return {
            'notifications': Notification.objects.filter(user=request.user, read=False)[:5],
            'notifications_unread': Notification.objects.filter(user=request.user, read=False).count()
        }
    return {}