# Generated by Django 3.1.2 on 2021-05-05 14:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('django_plastic_tickets', '0002_auto_20210423_2334'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ticket',
            name='message',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='state',
            field=models.CharField(choices=[('OP', 'Open'), ('RE', 'Rejected'), ('DO', 'Done')], default='OP', max_length=2),
        ),
    ]