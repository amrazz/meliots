# Generated by Django 5.0.3 on 2024-04-17 14:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cart_app", "0011_alter_orderitem_product"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="qty",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
