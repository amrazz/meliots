# Generated by Django 5.0.3 on 2024-03-22 09:30

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("admin_app", "0006_rename_image_productcolorimage_image1_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="product",
            name="quantity",
        ),
    ]
