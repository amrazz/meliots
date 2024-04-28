from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from admin_app.models import *
from accounts.models import *


# Create your models here.


class User_Cart(models.Model):
    customer = models.OneToOneField(Customer, on_delete = models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self) -> str:
        return f"Cart for {self.customer.user.username}"
    
@receiver(post_save, sender = Customer)
def create_customer_cart(sender, instance, created, **kwargs):
    if created:
        User_Cart.objects.create(customer=instance)
        print('cart customer created successfully!!')
        

class CartItem(models.Model):
    user_cart = models.ForeignKey(User_Cart, on_delete=models.CASCADE)
    product = models.ForeignKey(ProductColorImage, on_delete=models.CASCADE)
    product_size = models.CharField(max_length=10, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1, null=True, blank=True)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.product.name} - {self.product_size} - (Quantity: {self.quantity})"

    def total_price(self):
        offer_price = self.product.product.offer_price()
        return int(round(self.quantity * offer_price))
    

class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    address = models.ForeignKey(Address, on_delete=models.CASCADE)
    payment_method = models.CharField(max_length=100, null=False)
    payment_id = models.CharField(max_length=100, null=True)
    STATUS_CHOICES = (
    ('Order Placed', 'Order Placed'),
    ('Pending', 'Pending'),
    ('Shipped', 'Shipped'),
    ('Out for Delivery', 'Out for Delivery'),
    ('Delivered', 'Delivered'),
    ('Returned', 'Returned'),
    ('Refunded', 'Refunded'),
    ('Cancelled', 'Cancelled')
    ) 
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    tracking_id = models.CharField(max_length=100, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    subtotal = models.PositiveBigIntegerField(default=0, blank=True, null=True)
    shipping_charge = models.PositiveBigIntegerField(default=0, blank=True, null=True)
    total = models.IntegerField(default=0)
    paid = models.BooleanField(default=False)
    coupon_applied = models.BooleanField(default=False)
    coupon_name = models.CharField(blank=True, null=True)
    coupon_discount_percentage = models.PositiveBigIntegerField(blank=True, null=True)
    discounted_price = models.PositiveBigIntegerField(blank=True, default=0)

    

    
    def __str__(self) -> str:
        return f"{self.id} : {self.tracking_id}"
    
class OrderItem(models.Model):
    order = models.ForeignKey(Order,related_name='order', on_delete=models.CASCADE)
    product = models.ForeignKey(ProductColorImage, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    size = models.CharField(max_length = 12, default = 'S')
    qty = models.PositiveIntegerField(default=0)
    def __str__(self):
        return f"{self.product.product.name} - {self.size} - (Quantity: {self.qty})"

    def total_price(self):
        return self.cart_item.total_price()
    
class WishList(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    product = models.ForeignKey(ProductColorImage, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    qty = models.IntegerField(default = 1, null=True, blank=True)
    size = models.CharField(default='S', null=True, blank=True)
    def __str__(self) -> str:
        return f"{self.customer.user.username} :- {self.product.product.name} : {self.added_at}"