# Generated by Django 5.0.6 on 2025-03-19 03:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('client', '0004_order_finished_workers_order_notified_workers_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='order',
            old_name='is_finish',
            new_name='client_is_finished',
        ),
        migrations.AddField(
            model_name='order',
            name='worker_is_finished',
            field=models.BooleanField(default=False),
        ),
    ]
