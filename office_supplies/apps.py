from django.apps import AppConfig

class OfficeSuppliesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'office_supplies'
    label = 'office_supplies'  # Different label from vet_supplies