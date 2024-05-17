# Generated by Django 5.0.3 on 2024-05-16 14:09

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_rename_referred_code_customer_referred_person"),
        ("cart_app", "0035_alter_order_address"),
    ]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="address",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="accounts.address",
            ),
        ),
    ]
