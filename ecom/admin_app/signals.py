from django.dispatch import receiver
from django.db.models.signals import *
from .models import *



@receiver(pre_save, sender=Coupon)
def update_coupon_status(sender, instance, **kwargs):
    today = timezone.now()
    
    # Correctly compare expiry_date with today
    if str(instance.expiry_date) and str(instance.expiry_date) < str(today):
        print('Coupon has expired.')
        instance.is_active = False
    
        # Assuming usage_limit is the correct field to compare with used_count
    elif int(instance.usage_limit) is not None and int(instance.used_count) >= int(instance.usage_limit):
        print('Coupon usage limit reached.')
        instance.is_active = False
    else:
        print('Coupon is active.')
        instance.is_active = True