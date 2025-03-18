from reportlab.pdfgen import canvas  # Correct import for PDF generation
from django.views import View
from openpyxl import Workbook
import csv
from io import TextIOWrapper
from django.utils import timezone
from django.urls import reverse_lazy
from django.template.loader import render_to_string
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models import Q, F, Sum
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from .models import VetSupply, VetCategory, MassOutgoing, ExpiredItem, OfficeSupply
from .forms import MassOutgoingItemFormSet, VetSupplyForm, MassOutgoingForm, MassAddForm
from datetime import date, timedelta
from django.db.models.deletion import ProtectedError
from django.db import connection
from django.contrib.auth.decorators import login_required
import io
from datetime import datetime
from django.db.models import Q
from django.views.generic import ListView
from .models import MassOutgoingTransaction


# Authentication Views
class UserSignUpView(CreateView):
    form_class = UserCreationForm
    template_name = 'registration/signup.html'
    success_url = reverse_lazy('vet_supplies:supply-list')

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response

class UserLoginView(LoginView):
    template_name = 'registration/login.html'

class UserLogoutView(LogoutView):
    next_page = reverse_lazy('vet_supplies:supply-list')

# Vet Supply Views
class VetSupplyList(LoginRequiredMixin, ListView):
    model = VetSupply
    template_name = 'vet_supplies/list.html'
    context_object_name = 'supplies'
    paginate_by = 10

    def get_queryset(self):
        queryset = VetSupply.objects.select_related('category').all()
        search_query = self.request.GET.get('q')
        category_id = self.request.GET.get('category')
        stock_status = self.request.GET.get('stock_status')
        expiration_status = self.request.GET.get('expiration_status')

        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(category__name__icontains=search_query)
            )
        
        if category_id and category_id.isdigit():
            queryset = queryset.filter(category_id=category_id)
            
        if stock_status == 'low':
            queryset = queryset.filter(quantity__lte=F('reorder_level'))
        elif stock_status == 'normal':
            queryset = queryset.filter(quantity__gt=F('reorder_level'))

        # Handle expiration status filtering
        today = timezone.now().date()
        if expiration_status:
            if expiration_status == 'expired':
                queryset = queryset.filter(expiration_date__lt=today)
            elif expiration_status == 'expiring_soon':
                thirty_days_later = today + timedelta(days=30)
                queryset = queryset.filter(
                    expiration_date__gt=today,
                    expiration_date__lte=thirty_days_later
                )
            elif expiration_status == 'not_expiring':
                thirty_days_later = today + timedelta(days=30)
                queryset = queryset.filter(
                    Q(expiration_date__gt=thirty_days_later) | 
                    Q(expiration_date__isnull=True)
                )

        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        thirty_days_later = today + timedelta(days=30)
        
        context.update({
            'categories': VetCategory.objects.all(),
            'selected_category': self.request.GET.get('category', ''),
            'low_stock_count': VetSupply.objects.filter(
                quantity__lte=F('reorder_level')
            ).count(),
                'expiring_soon_count': VetSupply.objects.filter(
                expiration_date__gt=today,
                expiration_date__lte=thirty_days_later
            ).count(),
            'search_query': self.request.GET.get('q', ''),
            'selected_category': int(self.request.GET.get('category', 0) or 0),
            'stock_status': self.request.GET.get('stock_status', ''),
            'expiration_status': self.request.GET.get('expiration_status', '')
        })
        return context

# API endpoint to get supplies as JSON
def get_supplies_json(request):
    supplies = VetSupply.objects.all().values('name', 'quantity', 'reorder_level', 'expiration_date', 'expiration_status')
    return JsonResponse(list(supplies), safe=False)


class VetSupplyCreate(LoginRequiredMixin, CreateView):
    model = VetSupply
    form_class = VetSupplyForm
    template_name = 'vet_supplies/form.html'

    def get_success_url(self):
        return reverse_lazy('vet_supplies:supply-list')

class VetSupplyUpdate(LoginRequiredMixin, UpdateView):
    model = VetSupply
    form_class = VetSupplyForm
    template_name = 'vet_supplies/form.html'

    def get_success_url(self):
        return reverse_lazy('vet_supplies:supply-list')

class VetSupplyDelete(LoginRequiredMixin, DeleteView):
    model = VetSupply
    template_name = 'vet_supplies/confirm_delete.html'
    success_url = reverse_lazy('vet_supplies:supply-list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            self.object.delete()
            messages.success(request, 'Supply deleted successfully')
            return redirect(self.success_url)
        except ProtectedError:
            messages.error(request, 'Cannot delete this supply because it is referenced by other records')
            return redirect(self.success_url)

# Category Views
class VetCategoryList(LoginRequiredMixin, ListView):
    model = VetCategory
    template_name = 'vet_supplies/category_list.html'

class VetCategoryCreate(LoginRequiredMixin, CreateView):
    model = VetCategory
    template_name = 'vet_supplies/category_form.html'
    fields = ['name', 'description']
    success_url = reverse_lazy('vet_supplies:category-list')

class VetCategoryUpdate(LoginRequiredMixin, UpdateView):
    model = VetCategory
    fields = ['name']
    template_name = 'vet_supplies/category_form.html'
    success_url = reverse_lazy('vet_supplies:category-list')

class VetCategoryDelete(LoginRequiredMixin, DeleteView):
    model = VetCategory
    success_url = reverse_lazy('vet_supplies:category-list')
    template_name = 'vet_supplies/vetcategory_confirm_delete.html'

    def delete(self, request, *args, **kwargs):
        category = self.get_object()
        messages.success(request, f'Category "{category.name}" was successfully deleted.')
        return super().delete(request, *args, **kwargs)

class VetSupplyDetail(LoginRequiredMixin, DetailView):
    model = VetSupply
    template_name = 'vet_supplies/detail.html'

# Mass Outgoing View
class MassOutgoingCreateView(LoginRequiredMixin, CreateView):
    model = MassOutgoing
    form_class = MassOutgoingForm
    template_name = 'vet_supplies/mass_outgoing_form.html'
    success_url = reverse_lazy('vet_supplies:supply-list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = MassOutgoingItemFormSet(self.request.POST)
        else:
            context['formset'] = MassOutgoingItemFormSet()
        return context

    def form_valid(self, form):
        try:
            with transaction.atomic():
                form.instance.processed_by = self.request.user
                context = self.get_context_data()
                formset = context['formset']
                if formset.is_valid():
                    self.object = form.save()
                    formset.instance = self.object
                    formset.save()
                    # Removed success message
                    return redirect(self.success_url)
                return self.render_to_response(self.get_context_data(form=form))
        except IntegrityError:
            form.add_error(None, "Failed to create transaction. Please try again.")
            return self.form_invalid(form)

class ExpiredItemDeleteView(LoginRequiredMixin, DeleteView):
    model = ExpiredItem
    template_name = 'vet_supplies/confirm_delete.html'
    success_url = reverse_lazy('vet_supplies:expired-list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Expired item removed successfully')
        return super().delete(request, *args, **kwargs)

# Expired Item List View
class ExpiredItemListView(LoginRequiredMixin, ListView):
    model = ExpiredItem
    template_name = 'vet_supplies/expired_list.html'
    context_object_name = 'items'

    def get_queryset(self):
        return ExpiredItem.objects.all()

class MassAddView(LoginRequiredMixin, View):
    template_name = 'vet_supplies/mass_add.html'
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

                    category, _ = VetCategory.objects.get_or_create(name=row['Category'].strip())

                    VetSupply.objects.create(
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

        return redirect('mass-add')

class DownloadCSVTemplateView(View):
    def get(self, request, *args, **kwargs):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="template.csv"'

        writer = csv.writer(response)
        writer.writerow(['Column1', 'Column2', 'Column3'])  # Add your template columns here

        return response

class ExpiringSoonListView(LoginRequiredMixin, ListView):
    model = VetSupply
    template_name = 'vet_supplies/expiring_soon.html'
    context_object_name = 'supplies'

    def get_queryset(self):
        thirty_days_from_now = timezone.now().date() + timedelta(days=30)
        return VetSupply.objects.filter(
            expiration_date__lte=thirty_days_from_now,
            expiration_date__gt=timezone.now().date()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Items Expiring Soon'
        return context
    
    
# Low Stock List View to show items with low stock levels
class LowStockListView(LoginRequiredMixin, ListView):
    model = VetSupply
    template_name = 'vet_supplies/low_stock.html'
    context_object_name = 'supplies'

    def get_queryset(self):
        return VetSupply.objects.filter(quantity__lte=F('reorder_level'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Low Stock Items'
        return context

class ReportsView(LoginRequiredMixin, TemplateView):
    template_name = 'vet_supplies/reports.html'

    def get(self, request, *args, **kwargs):
        report_format = request.GET.get('format')
        report_type = request.GET.get('type')

        if report_format in ['pdf', 'excel']:
            queryset = VetSupply.objects.all()
            if report_type == 'low_stock':
                queryset = queryset.filter(quantity__lte=F('reorder_level'))
            elif report_type == 'expiring':
                queryset = queryset.filter(
                    expiration_date__lte=timezone.now().date() + timedelta(days=30),
                    expiration_date__gt=timezone.now().date()
                )
            
            if report_format == 'pdf':
                return self.generate_pdf(queryset, report_type)
            return self.generate_excel(queryset, report_type)
        
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get date range for filtering
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)

        # Fetch data with optimized queries using correct related name
        supplies = VetSupply.objects.select_related('category')\
            .annotate(total_used=Sum('vet_supply_transactions__quantity'))
        
        low_stock = supplies.filter(quantity__lte=F('reorder_level'))
        expiring_soon = supplies.filter(
            expiration_date__lte=timezone.now().date() + timedelta(days=30),
            expiration_date__gt=timezone.now().date()
        )

        context.update({
            'title': 'Inventory Reports',
            'total_supplies': supplies.count(),
            'low_stock_count': low_stock.count(),
            'expiring_soon_count': expiring_soon.count(),
            'supplies': supplies[:10],
            'low_stock': low_stock[:5],
            'expiring_soon': expiring_soon[:5],
            'start_date': start_date,
            'end_date': end_date,
        })
        
        return context

    def generate_pdf(self, queryset, report_type):
        response = HttpResponse(content_type='application/pdf')
        filename = f"inventory_report_{report_type}_{timezone.now().date()}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        p = canvas.Canvas(response)
        p.setFont("Helvetica-Bold", 16)
        p.drawString(50, 800, f"Inventory Report ({report_type.replace('_', ' ').title()})")
        
        y = 750
        p.setFont("Helvetica", 12)
        for supply in queryset:
            p.drawString(50, y, f"{supply.name}")
            p.drawString(200, y, f"Quantity: {supply.quantity}")
            p.drawString(350, y, f"Exp: {supply.expiration_date or 'N/A'}")
            y -= 20
            if y < 50:
                p.showPage()
                y = 800
        p.save()
        return response

    def generate_excel(self, queryset, report_type):
        response = HttpResponse(content_type='application/ms-excel')
        filename = f"vet_report_{report_type}_{timezone.now().date()}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        wb = Workbook()
        ws = wb.active
        ws.title = f"{report_type} Report"
        
        ws.append([
            'Name', 'Category', 'Quantity',
            'Reorder Level', 'Expiration Date', 'Status'
        ])
        
        for supply in queryset:
            ws.append([
                supply.name,
                supply.category.name,
                supply.quantity,
                supply.reorder_level,
                supply.expiration_date or 'N/A',
                supply.expiration_status
            ])
        
        wb.save(response)
        return response

# Remove or comment out the old reports_view function
# def reports_view(request):
#     return render(request, 'vet_supplies/reports.html')

class VetReportView(LoginRequiredMixin, View):
    report_types = {
        'expired': lambda: VetSupply.objects.expired(),
        'low_stock': lambda: VetSupply.objects.filter(quantity__lte=F('reorder_level')),
        'all': VetSupply.objects.all
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

    def generate_pdf(self, queryset, report_type):
        response = HttpResponse(content_type='application/pdf')
        filename = f"vet_report_{report_type}_{timezone.now().date()}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        # Correct instantiation of Canvas
        p = canvas.Canvas(response)
        p.setFont("Helvetica-Bold", 16)
        p.drawString(50, 800, f"Veterinary Supplies Report ({report_type.replace('_', ' ').title()})")

        y = 750
        p.setFont("Helvetica", 12)
        for supply in queryset:
            p.drawString(50, y, f"{supply.name}")
            p.drawString(200, y, f"Quantity: {supply.quantity}")
            p.drawString(350, y, f"Exp: {supply.expiration_date or 'N/A'}")
            y -= 20
            if y < 50:
                p.showPage()
                y = 800
        p.save()
        return response

    def generate_excel(self, queryset, report_type):
        response = HttpResponse(content_type='application/ms-excel')
        filename = f"vet_report_{report_type}_{timezone.now().date()}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        wb = Workbook()
        ws = wb.active
        ws.title = f"{report_type} Report"

        # Headers
        ws.append([
            'Name', 'Category', 'Quantity',
            'Reorder Level', 'Expiration Date', 'Status'
        ])

        # Data
        for supply in queryset:
            ws.append([
                supply.name,
                supply.category.name,
                supply.quantity,
                supply.reorder_level,
                supply.expiration_date or 'N/A',
                supply.expiration_status
            ])

        wb.save(response)
        return response

from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic.edit import DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import ProtectedError

class CategoryDelete(LoginRequiredMixin, DeleteView):
    model = VetCategory
    success_url = reverse_lazy('vet_supplies:category-list')
    template_name = 'vet_supplies/vetcategory_confirm_delete.html'

    def delete(self, request, *args, **kwargs):
        category = self.get_object()
        messages.success(request, f'Category "{category.name}" was successfully deleted.')
        return super().delete(request, *args, **kwargs)

class MassOutgoingListView(LoginRequiredMixin, ListView):
    model = MassOutgoing
    template_name = 'vet_supplies/mass_outgoing_list.html'
    context_object_name = 'transactions'
    paginate_by = 10

    def get_queryset(self):
        queryset = MassOutgoing.objects.prefetch_related('items', 'items__supply').order_by('-date')
        
        search_query = self.request.GET.get('search')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')

        if search_query:
            queryset = queryset.filter(
                Q(items__supply__name__icontains=search_query) |
                Q(reason__icontains=search_query) |
                Q(processed_by__username__icontains=search_query)
            ).distinct()

        if date_from:
            try:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
                queryset = queryset.filter(date__gte=date_from)
            except ValueError:
                pass

        if date_to:
            try:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
                queryset = queryset.filter(date__lte=date_to)
            except ValueError:
                pass

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'search': self.request.GET.get('search', ''),
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', '')
        })
        return context

def home(request):
    return render(request, 'home.html')

@login_required
def mass_add(request):
    if request.method == 'POST':
        form = MassAddForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                csv_file = request.FILES['csv_file']
                decoded_file = csv_file.read().decode('utf-8-sig')  # Handle BOM
                reader = csv.DictReader(io.StringIO(decoded_file))
                
                if not set(['name', 'quantity', 'category']).issubset(set(reader.fieldnames)):
                    raise ValueError("CSV must contain: name, quantity, category")
                
                items_data = []
                row_num = 1
                
                for row in reader:
                    row_num += 1
                    # Validate and clean data
                    if not row['name'].strip():
                        raise ValueError(f"Row {row_num}: Name cannot be empty")
                    
                    try:
                        quantity = int(row['quantity'].strip())
                        if quantity < 0:
                            raise ValueError
                    except ValueError:
                        raise ValueError(f"Row {row_num}: Invalid quantity - must be a positive number")
                    
                    if not row['category'].strip():
                        raise ValueError(f"Row {row_num}: Category cannot be empty")
                    
                    # Build item data
                    item_data = {
                        'name': row['name'].strip(),
                        'quantity': quantity,
                        'category': row['category'].strip(),
                        'reorder_level': int(row.get('reorder_level', '0').strip() or '0')
                    }
                    
                    # Handle expiration date with DD-MM-YYYY format
                    exp_date = row.get('expiration_date', '').strip()
                    if exp_date:
                        try:
                            # Replace any / or . with -
                            exp_date = exp_date.replace('/', '-').replace('.', '-')
                            parsed_date = datetime.strptime(exp_date, '%d-%m-%Y').date()
                            today = date.today()
                            if parsed_date < today:
                                raise ValueError(f"Row {row_num}: Expiration date cannot be in the past")
                            item_data['expiration_date'] = parsed_date
                        except ValueError as e:
                            if 'strptime' in str(e):
                                raise ValueError(f"Row {row_num}: Invalid date format - use DD-MM-YYYY (e.g., 31-12-2025)")
                            raise e
                    
                    items_data.append(item_data)
                
                # Process validated data
                with transaction.atomic():
                    for item in items_data:
                        category_obj, _ = VetCategory.objects.get_or_create(name=item['category'])
                        supply, created = VetSupply.objects.get_or_create(
                            name=item['name'],
                            defaults={
                                'category': category_obj,
                                'reorder_level': item['reorder_level'],
                                'quantity': 0
                            }
                        )
                        
                        if not created:
                            supply.category = category_obj
                            supply.reorder_level = item['reorder_level']
                        
                        if 'expiration_date' in item:
                            supply.expiration_date = item['expiration_date']
                        
                        supply.quantity += item['quantity']
                        supply.save()
                
                return redirect('vet_supplies:supply-list')
                
            except UnicodeDecodeError:
                form.add_error('csv_file', 'File must be in UTF-8 format')
            except ValueError as e:
                form.add_error('csv_file', str(e))
            except Exception as e:
                form.add_error('csv_file', f'Error processing file: {str(e)}')
    else:
        form = MassAddForm()
    
    return render(request, 'vet_supplies/mass_add.html', {'form': form})

@login_required
def download_template(request):
    response = HttpResponse(
        content_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename="vet_supplies_template.csv"'},
    )
    
    response.write(u'\ufeff')
    
    writer = csv.writer(response)
    writer.writerow(['name', 'quantity', 'category', 'reorder_level', 'expiration_date', 'dosage'])
    
    # Example data with consistent DD-MM-YYYY format using hyphens
    writer.writerow(['Amoxicillin', '100', 'Antibiotics', '50', '31-12-2025', '250mg'])
    writer.writerow(['Syringes', '200', 'Medical Supplies', '100', '', ''])
    writer.writerow(['Bandages', '300', 'First Aid', '150', '30-06-2026', ''])
    
    return response
