# Generated by Django 3.1.2 on 2021-04-23 21:34

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('django_plastic_tickets', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='assignee',
            field=models.ForeignKey(blank=True, help_text='The staff member who works on the ticket', null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='ticket',
            name='state',
            field=models.CharField(choices=[('OP', 'Open'), ('CL', 'Closed')], default='OP', max_length=2),
        ),
    ]
