# Generated by Django 5.0.3 on 2024-05-28 07:09

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cart_app", "0040_alter_order_status"),
    ]

    operations = [
        migrations.CreateModel(
            name="shipping_address",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("first_name", models.CharField(default=None, max_length=200)),
                ("last_name", models.CharField(default=None, max_length=200)),
                ("email", models.EmailField(default="user@gmail.com", max_length=254)),
                ("house_name", models.CharField(max_length=200)),
                ("city", models.CharField(max_length=100)),
                ("state", models.CharField(max_length=100)),
                ("postal_code", models.CharField(max_length=20)),
                ("country", models.CharField(max_length=100)),
                ("phone_number", models.CharField(max_length=12)),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="cart_app.order"
                    ),
                ),
            ],
        ),
    ]
