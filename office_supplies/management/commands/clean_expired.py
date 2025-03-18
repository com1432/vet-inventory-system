from django.core.management.base import BaseCommand
from office_supplies.models import OfficeSupply  # Assuming your model is in 'office_supplies'
from django.utils import timezone

class Command(BaseCommand):
    help = 'Removes expired items from inventory'

    def handle(self, *args, **options):
        expired_items = OfficeSupply.objects.filter(
            expiration_date__lte=timezone.now().date(),
            is_active=True
        )
        
        count = expired_items.count()
        expired_items.update(is_active=False)
        
        self.stdout.write(self.style.SUCCESS(
            f'Successfully removed {count} expired items'
        ))
