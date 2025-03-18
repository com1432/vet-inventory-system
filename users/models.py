from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    USER_TYPES = (
        ('admin', 'Administrator'),
        ('staff', 'Staff Member'),
        ('user', 'Regular User')
    )
    
    user_type = models.CharField(max_length=10, choices=USER_TYPES, default='user')
    email = models.EmailField(unique=True)
    is_email_verified = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"