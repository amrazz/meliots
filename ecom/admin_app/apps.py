from django.apps import AppConfig
from django.db.models.signals import pre_save


class AdminConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'admin_app'
    
    def ready(self):
        from . import signals