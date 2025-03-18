from itertools import count
from unicodedata import category
from django.forms import ValidationError
from django.views import View
import csv
from openpyxl import Workbook

from io import TextIOWrapper
from django.utils import timezone
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction, IntegrityError
from django.db.models import Q, F, Count, Sum

from vet_supplies.models import MassOutgoing
from .models import OfficeSupply, OfficeCategory, OfficeMassOutgoing
from .forms import MassOutgoingItemFormSet, OfficeSupplyForm, OfficeMassOutgoingForm, MassAddForm
from django.http import HttpResponse, JsonResponse
from datetime import datetime, timedelta
from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import CreateView
from django.urls import reverse_lazy
from .models import OfficeMassOutgoing
from .forms import OfficeMassOutgoingForm, MassOutgoingItemFormSet
from django.db import transaction
from django.core.exceptions import ValidationError

import io
from django.contrib.auth.decorators import login_required
from .models import OfficeMassIncoming

# Authentication Views
class UserSignUpView(CreateView):
    form_class = UserCreationForm
    template_name = 'registration/signup.html'
    success_url = reverse_lazy('office_supplies:supply-list')  # Updated
    
    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response

class UserLoginView(LoginView):
    template_name = 'registration/login.html'

class UserLogoutView(LogoutView):
    next_page = reverse_lazy('office_supplies:supply-list')  # Updated

# Office Supply Views
class OfficeSupplyList(LoginRequiredMixin, ListView):
    model = OfficeSupply
    template_name = 'office_supplies/list.html'
    context_object_name = 'supplies'
    paginate_by = 10

    def get_queryset(self):
        queryset = OfficeSupply.objects.all().order_by('name')
        
        # Search query
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(category__name__icontains=search_query) |
                Q(description__icontains=search_query)
            )

        # Category filter
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category_id=category)

        # Stock status filter
        stock_status = self.request.GET.get('stock_status')
        if stock_status == 'low':
            queryset = queryset.filter(quantity__lte=F('reorder_level'))
        elif stock_status == 'normal':
            queryset = queryset.filter(quantity__gt=F('reorder_level'))

        # Expiration status filter
        today = timezone.now().date()
        thirty_days_later = today + timedelta(days=30)
        expiration_status = self.request.GET.get('expiration_status')
        
        if (expiration_status == 'expired'):
            queryset = queryset.filter(expiration_date__lt=today)
        elif expiration_status == 'expiring_soon':
            queryset = queryset.filter(
                expiration_date__gte=today,
                expiration_date__lte=thirty_days_later
            )
        elif expiration_status == 'not_expiring':
            queryset = queryset.filter(
                Q(expiration_date__gt=thirty_days_later) |
                Q(expiration_date__isnull=True)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        thirty_days_later = today + timedelta(days=30)
        
        context.update({
            'categories': OfficeCategory.objects.all(),
            'selected_category': self.request.GET.get('category', ''),
            'search_query': self.request.GET.get('q', ''),
            'stock_status': self.request.GET.get('stock_status', ''),
            'expiration_status': self.request.GET.get('expiration_status', ''),
            'low_stock_count': OfficeSupply.objects.filter(
                quantity__lte=F('reorder_level')
            ).count(),
            'expiring_soon_count': OfficeSupply.objects.filter(
                expiration_date__gt=today,
                expiration_date__lte=thirty_days_later
            ).count(),
        })
        
        # Preserve query parameters in pagination
        if self.request.GET:
            query_params = self.request.GET.copy()
            if 'page' in query_params:
                del query_params['page']
            context['query_params'] = query_params.urlencode()
        
        return context

def get_supplies_json(request):
    supplies = OfficeSupply.objects.all().values('name', 'quantity', 'reorder_level', 'expiration_date', 'expiration_status')
    return JsonResponse(list(supplies), safe=False)

class OfficeSupplyListView(LoginRequiredMixin, ListView):
    model = OfficeSupply
    template_name = 'office_supplies/list.html'
    context_object_name = 'supplies'
    paginate_by = 10  # Adjust this number as needed

class OfficeSupplyCreate(LoginRequiredMixin, CreateView):
    model = OfficeSupply
    form_class = OfficeSupplyForm
    template_name = 'office_supplies/form.html'
    
    def get_success_url(self):
        return reverse_lazy('office_supplies:supply-list')

class OfficeSupplyUpdate(LoginRequiredMixin, UpdateView):
    model = OfficeSupply
    form_class = OfficeSupplyForm
    template_name = 'office_supplies/form.html'
    
    def get_success_url(self):
        return reverse_lazy('office_supplies:supply-list')

class OfficeSupplyDelete(DeleteView):
    model = OfficeSupply
    success_url = reverse_lazy('office_supplies:supply_list')
    template_name = 'office_supplies/officesupply_confirm_delete.html'

class OfficeSupplyDelete(LoginRequiredMixin, DeleteView):
    model = OfficeSupply
    template_name = 'office_supplies/confirm_delete.html'
    success_url = reverse_lazy('office_supplies:supply-list')

# Category Views
class OfficeCategoryList(LoginRequiredMixin, ListView):
    model = OfficeCategory
    template_name = 'office_supplies/category_list.html'
    context_object_name = 'categories'
    ordering = ['name']

class OfficeCategoryCreate(LoginRequiredMixin, CreateView):
    model = OfficeCategory
    template_name = 'office_supplies/category_form.html'
    fields = ['name', 'description']
    success_url = reverse_lazy('office_supplies:category-list')

class OfficeCategoryUpdate(LoginRequiredMixin, UpdateView):
    model = OfficeCategory
    fields = ['name']
    template_name = 'office_supplies/category_form.html'
    success_url = reverse_lazy('office_supplies:category-list')

class OfficeCategoryDelete(LoginRequiredMixin, DeleteView):
    model = OfficeCategory
    template_name = 'office_supplies/category_confirm_delete.html'
    success_url = reverse_lazy('office_supplies:category-list')

class OfficeSupplyDetail(LoginRequiredMixin, DetailView):
    model = OfficeSupply
    template_name = 'office_supplies/detail.html'


class OfficeMassOutgoingCreateView(LoginRequiredMixin, CreateView):
    model = OfficeMassOutgoing
    form_class = OfficeMassOutgoingForm
    template_name = 'office_supplies/mass_outgoing_form.html'
    success_url = reverse_lazy('office_supplies:mass-outgoing-list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = MassOutgoingItemFormSet(self.request.POST, instance=self.object)
        else:
            context['formset'] = MassOutgoingItemFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        form.instance.processed_by = self.request.user
        context = self.get_context_data()
        formset = context['formset']
        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            return redirect(self.success_url)
        return self.render_to_response(self.get_context_data(form=form))

    def form_invalid(self, form):
        context = self.get_context_data()
        context['form'] = form
        return self.render_to_response(context)

class OfficeMassOutgoingListView(LoginRequiredMixin, ListView):
    model = OfficeMassOutgoing
    template_name = 'office_supplies/mass_outgoing_list.html'
    context_object_name = 'transactions'
    ordering = ['-date']  # Changed from 'created_at' to 'date'

class ExpiredItemDeleteView(LoginRequiredMixin, DeleteView):
    model = OfficeSupply
    template_name = 'office_supplies/expired_confirm_delete.html'
    success_url = reverse_lazy('office_supplies:expired-list')

class ExpiredItemListView(LoginRequiredMixin, ListView):
    model = OfficeSupply
    template_name = 'office_supplies/expired_list.html'
    context_object_name = 'expired_items'

    def get_queryset(self):
        return OfficeSupply.objects.filter(expiration_date__lte=timezone.now().date())

class MassAddView(LoginRequiredMixin, View):
    template_name = 'office_supplies/mass_add.html'  # Updated template path
    form_class = MassAddForm

    def get(self, request):
        return render(request, self.template_name, {'form': self.form_class()})

    @transaction.atomic
    def post(self, request):
        form = self.form_class(request.POST, request.FILES)
        created_count = 0
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        try:
            csv_file = TextIOWrapper(request.FILES['csv_file'].file, encoding='utf-8-sig')
            reader = csv.DictReader(csv_file)

            created_count = 0
            errors = []

            for row_num, row in enumerate(reader, 1):
                try:
                    if not row.get('Category') or not row.get('Item Name') or not row.get('Quantity'):
                        raise ValueError('Missing required fields')

                    category, _ = OfficeCategory.objects.get_or_create(name=row['Category'].strip())

                    OfficeSupply.objects.create(
                        name=row['Item Name'].strip(),
                        category=category,
                        quantity=int(row['Quantity']),
                        reorder_level=int(row.get('Reorder Level', 10)),
                        expiration_date=row.get('Expiration Date') or None,
                        description=row.get('Description', '')
                    )
                    created_count += 1
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")

            if errors:
                messages.error(request, f"Completed with {len(errors)} errors")
                messages.info(request, "Error details: " + "; ".join(errors))
            else:
                messages.success(request, f"Successfully added {created_count} items")

        except Exception as e:
            messages.error(request, f"File processing error: {str(e)}")

        return redirect('office_supplies:mass-add')

class DownloadCSVTemplateView(View):
    def get(self, request, *args, **kwargs):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="office_supplies_template.csv"'

        writer = csv.writer(response)
        writer.writerow(['Category', 'Item Name', 'Quantity', 'Reorder Level', 'Expiration Date', 'Description'])

        return response

class ExpiringSoonListView(LoginRequiredMixin, ListView):
    model = OfficeSupply
    template_name = 'office_supplies/expiring_soon.html'
    context_object_name = 'supplies'

    def get_queryset(self):
        thirty_days_from_now = timezone.now().date() + timedelta(days=30)
        return OfficeSupply.objects.filter(
            expiration_date__lte=thirty_days_from_now,
            expiration_date__gt=timezone.now().date()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Office Items Expiring Soon'
        return context

class DownloadCSVTemplateView(View):
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="mass_add_template.csv"'

        writer = csv.writer(response)
        # Writing the headers for the CSV
        writer.writerow([
            'Category',
            'Item Name',
            'Quantity',
            'Reorder Level',
            'Expiration Date',
            'Description'
        ])
        # Sample data row
        writer.writerow([
            'Stationery',
            'Printer Paper',
            '50',
            '10',
            '2025-12-31',
            'A4 size 80gsm'
        ])

        return response


from django.http import HttpResponse
from reportlab.pdfgen import canvas
from django.utils import timezone

class OfficeReportView(View):
    report_types = {
        'expired': lambda: OfficeSupply.objects.filter(expiration_date__lte=timezone.now().date()),
        'low_stock': lambda: OfficeSupply.objects.filter(quantity__lte=F('reorder_level')),
        'all': OfficeSupply.objects.all
    }

    def get(self, request, *args, **kwargs):
        report_type = request.GET.get('type', 'all')
        format = request.GET.get('format', 'pdf')
        
        queryset = self.report_types.get(report_type, self.report_types['all'])()
        
        if format == 'pdf':
            return self.generate_pdf(queryset, report_type)
        elif format == 'excel':
            return self.generate_excel(queryset, report_type)
        return HttpResponse("Invalid format", status=400)

    def generate_excel(self, queryset, report_type):
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f"office_report_{report_type}_{timezone.now().date()}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        wb = Workbook()
        ws = wb.active
        ws.title = f"{report_type.title()} Report"

        # Headers
        headers = ['Name', 'Category', 'Quantity', 'Reorder Level', 'Status']
        ws.append(headers)

        # Data
        for item in queryset:
            ws.append([
                item.name,
                item.category.name,
                item.quantity,
                item.reorder_level,
                'Low Stock' if item.needs_reorder else 'OK'
            ])

        wb.save(response)
        return response

    def generate_pdf(self, queryset, report_type):
        # Create the response object for the PDF
        response = HttpResponse(content_type='application/pdf')
        filename = f"office_report_{report_type}_{timezone.now().date()}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        # Create a canvas object using the response
        p = canvas.Canvas(response)
        
        # Add some header text to the PDF
        p.setFont("Helvetica-Bold", 16)
        p.drawString(50, 800, f"Office Supplies Report - {report_type.replace('_', ' ').title()}")

        # Set the font for the rest of the text
        p.setFont("Helvetica", 12)

        y = 750
        for item in queryset:
            p.drawString(50, y, f"Name: {item.name}")
            p.drawString(200, y, f"Category: {item.category.name}")
            p.drawString(350, y, f"Quantity: {item.quantity}")
            p.drawString(500, y, f"Reorder Level: {item.reorder_level}")
            p.drawString(650, y, f"Status: {'Low Stock' if item.needs_reorder else 'OK'}")
            y -= 20

            # If we are near the bottom of the page, create a new page
            if y < 50:
                p.showPage()
                y = 800

        p.showPage()
        p.save()

        return response

class LowStockListView(LoginRequiredMixin, ListView):
    model = OfficeSupply
    template_name = 'office_supplies/low_stock_list.html'
    context_object_name = 'supplies'

    def get_queryset(self):
        return OfficeSupply.objects.select_related('category').filter(
            quantity__lte=F('reorder_level')
        ).order_by('quantity')

class ExpiringSoonListView(LoginRequiredMixin, ListView):
    model = OfficeSupply
    template_name = 'office_supplies/expiring_soon_list.html'
    context_object_name = 'supplies'

    def get_queryset(self):
        today = timezone.now().date()
        return OfficeSupply.objects.select_related('category').filter(
            expiration_date__gt=today,
            expiration_date__lte=today + timedelta(days=30)
        ).order_by('expiration_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['now'] = timezone.now().date()
        return context

class OfficeReportsView(LoginRequiredMixin, TemplateView):
    template_name = 'office_supplies/reports.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get date range for filtering
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)

        # Fetch office-specific data
        supplies = OfficeSupply.objects.select_related('category')
        
        # Add office-specific metrics
        context.update({
            'title': 'Office Supplies Inventory Report',
            'total_supplies': supplies.count(),
            'low_stock_count': supplies.filter(quantity__lte=F('reorder_level')).count(),
            'supplies': supplies.order_by('-last_updated')[:10],  # Most recently updated
            'low_stock': supplies.filter(quantity__lte=F('reorder_level'))[:5],
            'categories_summary': self.get_categories_summary(supplies),
            'monthly_usage': self.get_monthly_usage(),
            'start_date': start_date,
            'end_date': end_date,
        })
        
        return context

    def get_categories_summary(self, supplies):
        return supplies.values('category__name').annotate(
            total_items=Count('id'),
            total_quantity=Sum('quantity'),
            low_stock_items=Count(
                'id',
                filter=Q(quantity__lte=F('reorder_level'))
            )
        )

    def get_monthly_usage(self):
        thirty_days_ago = timezone.now() - timedelta(days=30)
        return OfficeSupply.objects.filter(
            last_updated__gte=thirty_days_ago
        ).values('name').annotate(
            usage=F('initial_quantity') - F('quantity')
        ).order_by('-usage')[:5]

class CategoryListView(LoginRequiredMixin, ListView):
    model = OfficeCategory
    template_name = 'office_supplies/category_list.html'
    paginate_by = 12

    def get_queryset(self):
        queryset = super().get_queryset().annotate(
            item_count=Count('officesupply'),
            low_stock_count=Count(
                'officesupply',
                filter=Q(officesupply__quantity__lte=F('officesupply__reorder_level'))
            )
        )
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(name__icontains=search_query)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get total items across all categories
        total_items = OfficeSupply.objects.count()
        
        # Get category stats
        categories = self.get_queryset()
        category_count = categories.count()
        
        # Calculate average items per category
        avg_items = round(total_items / category_count, 1) if category_count > 0 else 0
        
        # Add category item counts
        categories_with_counts = categories.annotate(
            item_count=Count('officesupply'),
            total_quantity=Sum('officesupply__quantity'),
            low_stock_count=Count(
                'officesupply',
                filter=Q(officesupply__quantity__lte=F('officesupply__reorder_level'))
            )
        )
        
        context.update({
            'total_items': total_items,
            'avg_items': avg_items,
            'categories_with_counts': categories_with_counts,
            'has_low_stock': OfficeSupply.objects.filter(
                quantity__lte=F('reorder_level')
            ).exists(),
        })
        return context

class MassOutgoingListView(LoginRequiredMixin, ListView):
    model = MassOutgoing
    template_name = 'office_supplies/mass_outgoing_list.html'
    context_object_name = 'transactions'
    paginate_by = 10
    ordering = ['-date']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_count'] = MassOutgoing.objects.count()
        return context

@login_required
def mass_add(request):
    if request.method == 'POST':
        form = MassAddForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                csv_file = TextIOWrapper(request.FILES['csv_file'].file, encoding='utf-8')
                reader = csv.DictReader(csv_file)
                field_map = {h.lower(): h for h in reader.fieldnames} if reader.fieldnames else {}

                for row in reader:
                    try:
                        # Get data from CSV, using case-insensitive column names
                        name = row[field_map['name']].strip()
                        quantity = int(row[field_map['quantity']].strip())
                        category = row[field_map['category']].strip()
                        # Look for 'Expiry Date' with both cases
                        expiry_date = (row.get('Expiry Date', '') or row.get('expiry date', '')).strip()
                        
                        if not all([name, quantity, category]):
                            continue

                        category_obj, _ = OfficeCategory.objects.get_or_create(name=category)

                        # Convert expiry date string to date object
                        expiration_date = None
                        if expiry_date:
                            expiration_date = datetime.strptime(expiry_date, '%d-%m-%Y').date()

                        OfficeSupply.objects.create(
                            name=name,
                            category=category_obj,
                            quantity=quantity,
                            expiration_date=expiration_date,
                            reorder_level=10  # Default value
                        )

                    except Exception as e:
                        print(f"Error processing row: {str(e)}")  # Debug info
                        continue

                return redirect('office_supplies:supply-list')

            except Exception as e:
                print(f"File error: {str(e)}")  # Debug info
                return redirect('office_supplies:mass-add')
    else:
        form = MassAddForm()
    
    return render(request, 'office_supplies/mass_add.html', {'form': form})

@login_required
def download_template(request):
    response = HttpResponse(
        content_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename="office_supplies_template.csv"'},
    )
    
    response.write(u'\ufeff')
    
    writer = csv.writer(response)
    writer.writerow(['name', 'quantity', 'category', 'Expiry Date'])
    writer.writerow(['Sticky Notes', '100', 'Office Supplies', '31-12-2024'])
    writer.writerow(['Stapler', '25', 'Office Equipment', '15-06-2024'])
    writer.writerow(['Printer Paper', '500', 'Paper Products', '01-03-2025'])
    
    return response

from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url='/vet/', permanent=False)),
    path('vet/', include('vet_supplies.urls')),
    path('office/', include('office_supplies.urls')),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
]