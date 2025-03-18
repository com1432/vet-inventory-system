from django.contrib import admin
from .models import VetCategory, VetSupply


@admin.register(VetSupply)
class VetSupplyAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'quantity', 'expiration_status_display')
    list_filter = ('category', 'expiration_date')  # Use actual database fields
    search_fields = ('name', 'description')
    
    def expiration_status_display(self, obj):
        return obj.expiration_status.title()
    expiration_status_display.short_description = 'Expiration Status'

@admin.register(VetCategory)
class VetCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)