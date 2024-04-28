# Generated by Django 5.0.3 on 2024-04-24 15:29

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_app', '0010_remove_product_old_price_product_percentage'),
    ]

    operations = [
        migrations.CreateModel(
            name='Coupon',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('coupon_code', models.CharField(max_length=100, unique=True)),
                ('coupon_name', models.CharField(max_length=50)),
                ('discount_percentage', models.DecimalField(decimal_places=2, max_digits=5)),
                ('discount_value', models.PositiveBigIntegerField()),
                ('is_active', models.BooleanField(default=True)),
                ('added_date', models.DateTimeField(auto_now_add=True)),
                ('expiry_date', models.DateTimeField(blank=True, null=True)),
                ('usage_limit', models.PositiveIntegerField(blank=True, null=True)),
                ('used_count', models.PositiveIntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='CategoryOffer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('discount_percentage', models.PositiveIntegerField()),
                ('start_date', models.DateField(auto_now_add=True)),
                ('end_date', models.DateField()),
                ('category', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='admin_app.category')),
            ],
        ),
    ]