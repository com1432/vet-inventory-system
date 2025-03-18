from django.urls import path
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.conf.urls.static import static
from .views import (
    UserSignUpView, UserLoginView, UserLogoutView,
    OfficeSupplyList, OfficeSupplyCreate, OfficeSupplyUpdate, 
    OfficeSupplyDelete, OfficeSupplyDetail,
    OfficeCategoryList, OfficeCategoryCreate, OfficeCategoryUpdate, 
    OfficeCategoryDelete, OfficeMassOutgoingCreateView,
    ExpiredItemListView, ExpiredItemDeleteView,
    MassAddView, DownloadCSVTemplateView,
    
    OfficeReportView, LowStockListView, ExpiringSoonListView,
    OfficeReportsView, OfficeMassOutgoingListView
)
from django.contrib.auth import views as auth_views
from . import views

app_name = 'office_supplies'

urlpatterns = [
    # Authentication URLs
    path('signup/', UserSignUpView.as_view(), name='signup'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    
    # Supplies
    path('', OfficeSupplyList.as_view(), name='supply-list'),
    path('supplies/', OfficeSupplyList.as_view(), name='supply-list'),
    path('supplies/create/', OfficeSupplyCreate.as_view(), name='supply-create'),
    path('supplies/<int:pk>/', OfficeSupplyDetail.as_view(), name='supply-detail'),
    path('supplies/<int:pk>/update/', OfficeSupplyUpdate.as_view(), name='supply-update'),
    path('supplies/<int:pk>/delete/', OfficeSupplyDelete.as_view(), name='supply-delete'),
    path('supplies/<int:pk>/delete/', OfficeSupplyDelete.as_view(), name='supply_delete'),
    
    # Operations
    path('operations/outgoing/', OfficeMassOutgoingCreateView.as_view(), name='mass-outgoing-create'),
    path('operations/outgoing/list/', OfficeMassOutgoingListView.as_view(), name='mass-outgoing-list'),
    path('operations/mass-add/', MassAddView.as_view(), name='mass-add'),
    path('operations/mass-add-template/', DownloadCSVTemplateView.as_view(), name='download-csv-template'),
    path('mass-add/', views.mass_add, name='mass-add'),
    
    # Categories
    path('categories/', OfficeCategoryList.as_view(), name='category-list'),
    path('categories/new/', OfficeCategoryCreate.as_view(), name='category-create'),
    path('categories/<int:pk>/edit/', OfficeCategoryUpdate.as_view(), name='category-update'),
    path('categories/<int:pk>/delete/', OfficeCategoryDelete.as_view(), name='category-delete'),
    
    # Notifications

    
    # Reports
    path('reports/', OfficeReportView.as_view(), name='reports'),
    path('low-stock/', LowStockListView.as_view(), name='low-stock'),
    path('expiring-soon/', ExpiringSoonListView.as_view(), name='expiring-soon'),
    path('reports/', OfficeReportsView.as_view(), name='office-reports'),
    
    # Expired Items
    path('expired/', ExpiredItemListView.as_view(), name='expired-list'),
    path('expired/<int:pk>/delete/', ExpiredItemDeleteView.as_view(), name='expired-delete'),
    
    # Password Reset
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset.html',
        email_template_name='registration/password_reset_email.html',
        subject_template_name='registration/password_reset_subject.txt'
    ), name='office-password-reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'
    ), name='office-password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html'
    ), name='office-password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'
    ), name='office-password_reset_complete'),
    path('download-template/', views.download_template, name='download-template'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)