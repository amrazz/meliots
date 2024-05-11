from django.dispatch import receiver
from django.db.models.signals import *
from .models import *


@receiver(pre_save, sender=Coupon)
def update_coupon_status(sender, instance, **kwargs):
    today = timezone.now()

    if str(instance.expiry_date) and str(instance.expiry_date) < str(today):
        print("Coupon has expired.")
        instance.is_active = False
    elif int(instance.usage_limit) is not None and int(instance.used_count) >= int(
        instance.usage_limit
    ):
        print("Coupon usage limit reached.")
        instance.is_active = False
    else:
        print("Coupon is active.")
        instance.is_active = True
        

@receiver(post_save, sender=Product)
def update_product_status(sender, instance, created, **kwargs):
    today = timezone.now()
    if str(instance.per_expiry_date) and str(instance.per_expiry_date) < str(today):
        product = Product.objects.get(id=instance.id)
        product.percentage = 0
        product.save()

@receiver(post_save, sender=CategoryOffer)
def update_category_offer(sender, instance, created, **kwargs):
    today = timezone.now()
    if str(instance.end_date) and str(instance.end_date) < str(today):
        category_offer = CategoryOffer.objects.get(id=instance.id)
        category_offer.is_active = False
        category_offer.save()
