from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.conf import settings


class OfficeCategory(models.Model):
    name = models.CharField(
        max_length=100, 
        unique=True,
        error_messages={'unique': 'This category already exists.'}
    )
    description = models.TextField(blank=True, default="")

    class Meta:
        verbose_name_plural = "Office Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class OfficeSupply(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey('OfficeCategory', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    reorder_level = models.PositiveIntegerField(default=10)
    expiration_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Office Supplies"

    def __str__(self):
        return self.name

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


class OfficeMassOutgoing(models.Model):
    reason = models.CharField(max_length=255)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='office_mass_outgoings'
    )
    date = models.DateTimeField(default=timezone.now)
    supplies = models.ManyToManyField(
        'OfficeSupply',
        through='OfficeMassOutgoingItem',
        related_name='mass_outgoing_transactions'
    )

    class Meta:
        db_table = 'office_mass_outgoing'

    def __str__(self):
        return f"{self.date.strftime('%Y-%m-%d %H:%M')} - {self.reason}"


class OfficeMassOutgoingItem(models.Model):
    mass_outgoing = models.ForeignKey(
        OfficeMassOutgoing,
        on_delete=models.CASCADE,
        related_name='outgoing_items',
        null=True,  # Add this temporarily
        blank=True  # Add this temporarily
    )
    supply = models.ForeignKey(
        'OfficeSupply',
        on_delete=models.CASCADE,
        related_name='outgoing_items'
    )
    quantity = models.PositiveIntegerField()

    class Meta:
        db_table = 'office_mass_outgoing_items'

    def clean(self):
        if not self.supply or not self.quantity:
            raise ValidationError('Both supply and quantity are required.')
            
        if self.quantity > self.supply.quantity:
            raise ValidationError(f'Not enough {self.supply.name} in stock. Available: {self.supply.quantity}')

    def __str__(self):
        return f"{self.supply.name} - {self.quantity}"


class OfficeMassIncoming(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='office_mass_incoming'
    )
    items = models.JSONField(default=dict)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Mass Incoming Record'
        verbose_name_plural = 'Mass Incoming Records'

    def __str__(self):
        return f"Mass Import on {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

