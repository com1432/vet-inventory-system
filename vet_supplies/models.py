from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db.models import Q, F
from django.contrib.auth import get_user_model
import random
import string

User = get_user_model()


# VetCategory Model
class VetCategory(models.Model):
    name = models.CharField(
        max_length=100, 
        unique=True,
        error_messages={'unique': 'This category already exists.'}
    )
    description = models.TextField(blank=True, default="")
    alert_threshold = models.PositiveIntegerField(
        default=0,
        help_text="Minimum quantity to trigger alerts (0 to disable)"
    )

    class Meta:
        verbose_name_plural = "Vet Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


# VetSupply Model
class VetSupply(models.Model):
    name = models.CharField(max_length=200)
    quantity = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


# VetSupply Model
class VetSupply(models.Model):
    name = models.CharField(max_length=255)
    category = models.ForeignKey(
        VetCategory, 
        on_delete=models.CASCADE,
        related_name="supplies"
    )
    quantity = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)]
    )
    reorder_level = models.PositiveIntegerField(
        default=10,
        validators=[MinValueValidator(1)]
    )
    last_updated = models.DateTimeField(auto_now=True)
    description = models.TextField(blank=True)
    expiration_date = models.DateField(
        null=True, 
        blank=True,
        verbose_name="Expiration Date (optional)"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Vet Supplies"
        ordering = ['-last_updated']
        constraints = [
            models.CheckConstraint(
                check=models.Q(quantity__gte=0),
                name="vet_supply_quantity_positive"
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.category})"

    def get_absolute_url(self):
        return reverse('vet-supply-detail', kwargs={'pk': self.pk})
    
    @property
    def needs_reorder(self):
        return self.quantity <= self.reorder_level
    
    @property
    def expiration_status(self):
        if not self.expiration_date:
            return 'non-expiring'
            
        today = timezone.now().date()
        delta = (self.expiration_date - today).days
        
        if delta < 0:
            return 'expired'
        if delta <= 7:
            return 'critical'
        if delta <= 30:
            return 'warning'
        return 'ok'

    def clean(self):
        if self.expiration_date and self.expiration_date < timezone.now().date():
            raise ValidationError({
                'expiration_date': 'Expiration date cannot be in the past'
            })
        
        if self.reorder_level >= 1000:
            raise ValidationError({
                'reorder_level': 'Reorder level is unrealistically high (max 999)'
            })
        
        if self.quantity < 0:
            raise ValidationError({
                'quantity': 'Quantity cannot be negative'
            })

    def save(self, *args, **kwargs):
        # Check if expiration_date is in the past
        if self.expiration_date and self.expiration_date < timezone.now().date():
            self.expiration_date = None  # or handle it as needed
        self.full_clean()
        super().save(*args, **kwargs)
        
    def delete_if_expired(self):
        if self.expiration_status == 'expired':
            self.is_active = False
            self.save()


# ExpiredItem Model
class ExpiredItem(models.Model):
    supply = models.ForeignKey(VetSupply, on_delete=models.CASCADE)
    expiration_date = models.DateField()


# MassOutgoing Model
class MassOutgoing(models.Model):
    transaction_id = models.CharField(max_length=100, unique=True)
    date = models.DateTimeField(auto_now_add=True)
    reason = models.TextField()
    patient_name = models.CharField(max_length=200, blank=True, default='')
    doctor_name = models.CharField(max_length=200, blank=True, default='')
    processed_by = models.ForeignKey(
        User, 
        on_delete=models.PROTECT,
        related_name='vet_mass_outgoings'
    )
    supplies = models.ManyToManyField(
        'VetSupply', 
        through='MassOutgoingItem',
        related_name='vet_outgoing_transactions'
    )

    def __str__(self):
        return f"Vet Outgoing {self.date.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['-date']

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            date_string = timezone.now().strftime('%Y%m%d')
            random_string = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            self.transaction_id = f"OUT-{date_string}-{random_string}"
        super().save(*args, **kwargs)


# MassOutgoingItem Model
class MassOutgoingItem(models.Model):
    mass_outgoing = models.ForeignKey(
        MassOutgoing, 
        on_delete=models.CASCADE,
        related_name='items',
        null=True,  # Add this to make the field nullable
        blank=True  # Add this to make the field optional in forms
    )
    supply = models.ForeignKey(
        'VetSupply', 
        on_delete=models.CASCADE,
        related_name='vet_supply_transactions'
    )
    quantity = models.PositiveIntegerField()
    
    def clean(self):
        if self.quantity > self.supply.quantity:
            raise ValidationError(
                f"Not enough stock. Available: {self.supply.quantity}"
            )

    def save(self, *args, **kwargs):
        self.supply.quantity -= self.quantity
        self.supply.save()
        super().save(*args, **kwargs)


# Notification Model
class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('low_stock', 'Low Stock'),
        ('expiring', 'Expiring Soon'),
        ('expired', 'Expired'),
        ('out_of_stock', 'Out of Stock'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='vet_notifications'
    )
    supply = models.ForeignKey(
        'VetSupply',
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Inventory Notification'
        verbose_name_plural = 'Inventory Notifications'

    def __str__(self):
        return f"{self.get_notification_type_display()} - {self.supply.name}"

    @classmethod
    def create_alert(cls, supply, notification_type):
        """Create notifications for relevant users"""
        users = User.objects.filter(
            Q(is_superuser=True) |
            Q(groups__name='Inventory Managers')
        ).distinct()

        for user in users:
            cls.objects.get_or_create(
                user=user,
                supply=supply,
                notification_type=notification_type,
                defaults={
                    'message': cls.generate_message(supply, notification_type),
                    'resolved': False
                }
            )

    @classmethod
    def generate_message(cls, supply, notification_type):
        """Generate context-aware messages"""
        # Check for expiration_date being None
        if notification_type in ['expiring', 'expired'] and not supply.expiration_date:
            return f"{supply.name} has no expiration date specified."

        messages = {
            'low_stock': (
                f"Low stock alert for {supply.name}. "
                f"Current quantity: {supply.quantity} "
                f"(Reorder level: {supply.reorder_level})"
            ),
            'expiring': (
                f"{supply.name} expires on {supply.expiration_date.strftime('%Y-%m-%d')}. "
                f"Quantity affected: {supply.quantity}"
            ),
            'expired': (
                f"{supply.name} expired on {supply.expiration_date.strftime('%Y-%m-%d')}. "
                f"Quantity affected: {supply.quantity}"
            ),
            'out_of_stock': f"{supply.name} is out of stock!"
        }

        return messages.get(notification_type, "Inventory Alert")


# OfficeCategory Model
class OfficeCategory(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


# OfficeSupply Model
class OfficeSupply(models.Model):
    name = models.CharField(max_length=255)
    category = models.ForeignKey(OfficeCategory, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    reorder_level = models.PositiveIntegerField(default=10)
    expiration_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)  # Added is_active field

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(quantity__gte=0),
                name='vet_supplies_quantity_positive'
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.category})"

    def get_absolute_url(self):
        return reverse('office-supply-detail', kwargs={'pk': self.pk})

    @property
    def needs_reorder(self):
        return self.quantity <= self.reorder_level

    @property
    def expiration_status(self):
        if not self.expiration_date:
            return 'non-expiring'

        today = timezone.now().date()
        delta = (self.expiration_date - today).days

        if delta < 0:
            return 'expired'
        if delta <= 7:
            return 'critical'
        if delta <= 30:
            return 'warning'
        return 'ok'

    def clean(self):
        """Combined validation rules"""
        if self.expiration_date and self.expiration_date < timezone.now().date():
            raise ValidationError({
                'expiration_date': 'Expiration date cannot be in the past'
            })

        if self.reorder_level >= 1000:
            raise ValidationError({
                'reorder_level': 'Reorder level is unrealistically high (max 999)'
            })

        if self.quantity < 0:
            raise ValidationError({
                'quantity': 'Quantity cannot be negative'
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def delete_if_expired(self):
        if self.expiration_status == 'expired':
            self.is_active = False
            self.save()


# StockMovement Model
class StockMovement(models.Model):
    supply = models.ForeignKey(VetSupply, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    movement_type = models.CharField(max_length=10, choices=[('in', 'In'), ('out', 'Out')])
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)


# Remove or comment out the Treatment model if it exists
# class Treatment(models.Model):
#     ...



class VetSupplyTransaction(models.Model):
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )


class MassOutgoingTransaction(models.Model):
    transaction_id = models.CharField(max_length=100, unique=True)
    supply = models.ForeignKey('VetSupply', on_delete=models.CASCADE)  # Changed from 'Supply' to 'VetSupply'
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    patient_name = models.CharField(max_length=200)
    doctor_name = models.CharField(max_length=200)
    notes = models.TextField(blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_id} - {self.supply.name}"

    class Meta:
        ordering = ['-date_created']
