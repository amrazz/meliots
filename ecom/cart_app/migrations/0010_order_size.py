# Generated by Django 5.0.3 on 2024-04-17 14:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cart_app', '0009_alter_orderitem_product'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='size',
            field=models.CharField(default='S', max_length=12),
        ),
    ]
