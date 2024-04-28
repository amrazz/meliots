# Generated by Django 5.0.3 on 2024-03-21 11:45

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_app', '0004_product_is_deleted_product_is_listed_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='category',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='category', to='admin_app.category'),
            preserve_default=False,
        ),
    ]