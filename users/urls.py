from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('verify-email/<str:uidb64>/<str:token>/', views.verify_email, name='verify-email'),
    # ...existing URL patterns...
]