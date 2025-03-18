from django.contrib import admin
from .models import OfficeCategory, OfficeSupply, OfficeMassIncoming  # Changed model imports

@admin.register(OfficeSupply)  # Changed to OfficeSupply
class OfficeSupplyAdmin(admin.ModelAdmin):  # Renamed class
    list_display = ('name', 'category', 'quantity', 'expiration_status_display')
    list_filter = ('category', 'expiration_date')
    search_fields = ('name', 'description')
    
    def expiration_status_display(self, obj):
        return obj.expiration_status.title()
    expiration_status_display.short_description = 'Expiration Status'

@admin.register(OfficeCategory)  # Changed to OfficeCategory
class OfficeCategoryAdmin(admin.ModelAdmin):  # Renamed class
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(OfficeMassIncoming)
class OfficeMassIncomingAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'processed_by', 'notes']
    list_filter = ['timestamp', 'processed_by']
    readonly_fields = ['timestamp', 'processed_by', 'items']
    search_fields = ['notes']
    
    def has_add_permission(self, request):
        return False  # Prevent manual creation