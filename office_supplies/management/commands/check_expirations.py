from django.core.management.base import BaseCommand
from django.utils import timezone
from office_supplies.models import OfficeSupply, Notification
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Checks for expiring supplies and generates notifications'

    def handle(self, *args, **options):
        # Check expiring items
        for supply in OfficeSupply.objects.filter(expiration_date__isnull=False):
            supply.save()  # This will trigger the post_save signal
