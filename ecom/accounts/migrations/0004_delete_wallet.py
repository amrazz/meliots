# Generated by Django 5.0.3 on 2024-05-04 12:09

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_wallet"),
    ]

    operations = [
        migrations.DeleteModel(
            name="Wallet",
        ),
    ]