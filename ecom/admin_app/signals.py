from django.dispatch import receiver
from django.db.models.signals import *
from .models import *

@receiver(pre_save, sender=Coupon)
def update_coupon_status(sender, instance, **kwargs):
    if instance.expiry_date and timezone.now() > instance.expiry_date:
        instance.is_active = False
    elif instance.usage_limit and instance.used_count >= instance.usage_limit:
        instance.is_active = False
    else:
        instance.is_active = True
