from django import forms
from .models import VetSupply, MassOutgoing, MassOutgoingItem

class VetSupplyForm(forms.ModelForm):
    class Meta:
        model = VetSupply
        fields = ['name', 'category', 'quantity', 'reorder_level', 'expiration_date', 'description']
        widgets = {
            'expiration_date': forms.DateInput(attrs={'type': 'date'}),
            'reorder_level': forms.NumberInput(attrs={'min': 1}),
            'quantity': forms.NumberInput(attrs={'min': 0}),
        }
        labels = {
            'reorder_level': 'Reorder Level (alert when stock reaches this number)',
            'expiration_date': 'Expiration Date (optional)'
        }

class MassOutgoingForm(forms.ModelForm):
    class Meta:
        model = MassOutgoing
        fields = ['reason']

MassOutgoingItemFormSet = forms.inlineformset_factory(
    MassOutgoing,
    MassOutgoingItem,
    fields=('supply', 'quantity'),
    extra=1,
    widgets={
        'supply': forms.Select(attrs={'class': 'select2'}),
        'quantity': forms.NumberInput(attrs={'min': 1})
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