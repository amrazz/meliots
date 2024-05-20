# Generated by Django 5.0.3 on 2024-05-12 12:47

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cart_app", "0029_wallet_wallet_transaction"),
    ]

    operations = [
        migrations.AlterField(
            model_name="wallet_transaction",
            name="order_item",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="cart_app.orderitem",
            ),
        ),
    ]