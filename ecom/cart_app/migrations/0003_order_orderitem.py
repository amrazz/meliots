# Generated by Django 5.0.3 on 2024-04-14 11:19

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_address'),
        ('cart_app', '0002_alter_cartitem_product_size'),
    ]

    operations = [
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payment_method', models.CharField(max_length=100)),
                ('payment_id', models.CharField(max_length=100, null=True)),
                ('status', models.CharField(choices=[('Order Placed', 'Order Placed'), ('Pending', 'Pending'), ('Shipped', 'Shipped'), ('Out for Delivery', 'Out for Delivery'), ('Delivered', 'Delivered'), ('Returned', 'Returned'), ('Refunded', 'Refunded'), ('Cancelled', 'Cancelled')], max_length=20)),
                ('tracking_id', models.CharField(max_length=100, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('address', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.address')),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cart_app.user_cart')),
            ],
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cart_app.order')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cart_app.cartitem')),
            ],
        ),
    ]