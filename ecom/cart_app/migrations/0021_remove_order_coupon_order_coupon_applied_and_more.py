# Generated by Django 5.0.3 on 2024-04-24 15:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cart_app', '0020_order_coupon'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='coupon',
        ),
        migrations.AddField(
            model_name='order',
            name='coupon_applied',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='order',
            name='coupon_discount_percentage',
            field=models.PositiveBigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='coupon_name',
            field=models.CharField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='discounted_price',
            field=models.PositiveBigIntegerField(blank=True, default=0),
        ),
        migrations.AddField(
            model_name='order',
            name='paid',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='order',
            name='shipping_charge',
            field=models.PositiveBigIntegerField(blank=True, default=0, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='subtotal',
            field=models.PositiveBigIntegerField(blank=True, default=0, null=True),
        ),
    ]
