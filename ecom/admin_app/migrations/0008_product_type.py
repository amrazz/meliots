# Generated by Django 5.0.3 on 2024-03-28 03:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("admin_app", "0007_remove_product_quantity"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="type",
            field=models.CharField(default="Clothing", max_length=100),
        ),
    ]
