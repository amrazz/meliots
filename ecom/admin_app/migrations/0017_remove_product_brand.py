# Generated by Django 5.0.3 on 2024-05-08 05:31

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("admin_app", "0016_brand_product_brand"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="product",
            name="brand",
        ),
    ]
