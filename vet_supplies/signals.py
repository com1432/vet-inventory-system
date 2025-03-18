from datetime import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import VetSupply, Notification

@receiver(post_save, sender=VetSupply)
def create_supply_notifications(sender, instance, **kwargs):
    # Low stock notification
    if instance.quantity <= instance.reorder_level and instance.quantity > 0:
        Notification.objects.create(
            user=instance.category.user,  # Adjust based on your ownership structure
            supply=instance,
            notification_type='low_stock',
            message=f"{instance.name} is low on stock ({instance.quantity} remaining)"
        )
    
    # Out of stock notification
    if instance.quantity == 0:
        Notification.objects.create(
            user=instance.category.user,
            supply=instance,
            notification_type='out_of_stock',
            message=f"{instance.name} is out of stock"
        )
    
    # Expiration notifications
    if instance.expiration_date:
        today = timezone.now().date()
        delta = (instance.expiration_date - today).days
        
        if delta == 30:
            Notification.objects.create(
                user=instance.category.user,
                supply=instance,
                notification_type='expiring',
                message=f"{instance.name} expires in 30 days"
            )
        elif delta == 7:
            Notification.objects.create(
                user=instance.category.user,
                supply=instance,
                notification_type='expiring',
                message=f"{instance.name} expires in 7 days"
            )
        elif delta < 0:
            Notification.objects.create(
                user=instance.category.user,
                supply=instance,
                notification_type='expired',
                message=f"{instance.name} has expired"
            )