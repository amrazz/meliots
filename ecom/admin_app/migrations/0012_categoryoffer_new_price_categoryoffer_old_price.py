# Generated by Django 5.0.3 on 2024-04-24 16:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("admin_app", "0011_coupon_categoryoffer"),
    ]

    operations = [
        migrations.AddField(
            model_name="categoryoffer",
            name="new_price",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="categoryoffer",
            name="old_price",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
