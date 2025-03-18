import csv
import io
from django import forms
from datetime import datetime
from .models import OfficeSupply, OfficeMassOutgoing, OfficeMassOutgoingItem

class OfficeSupplyForm(forms.ModelForm):
    class Meta:
        model = OfficeSupply
        fields = ['name', 'category', 'quantity', 'reorder_level', 'expiration_date', 'description']
        widgets = {
            'expiration_date': forms.DateInput(attrs={'type': 'date'}),
            'reorder_level': forms.NumberInput(attrs={'min': 1}),
            'quantity': forms.NumberInput(attrs={'min': 0}),
        }
        labels = {
            'name': 'Item Name',
            'category': 'Category',
            'quantity': 'Quantity',
            'reorder_level': 'Reorder Level',
            'expiration_date': 'Expiration Date',
            'description': 'Description'
        }

class OfficeMassOutgoingForm(forms.ModelForm):
    class Meta:
        model = OfficeMassOutgoing
        fields = ['reason']
        labels = {
            'reason': 'Reason for Outgoing Items'
        }

MassOutgoingItemFormSet = forms.inlineformset_factory(
    OfficeMassOutgoing,
    OfficeMassOutgoingItem,
    fields=['supply', 'quantity'],
    extra=1,
    can_delete=True,
    labels={
        'supply': 'Item',
        'quantity': 'Quantity'
    }
)

class MassAddForm(forms.Form):
    csv_file = forms.FileField(
        label='Select CSV file',
        help_text='Upload a CSV file with dates in DD-MM-YYYY format (e.g., 31-12-2025). Use hyphens (-) as separators.'
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False
    )

    def clean_csv_file(self):
        file = self.cleaned_data['csv_file']
        if not file.name.endswith('.csv'):
            raise forms.ValidationError('File must be a CSV file')
        return file
    
class YourMassAddForm(forms.Form):
    file = forms.FileField(required=True)