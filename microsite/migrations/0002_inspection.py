# Generated by Django 4.1.5 on 2024-02-13 07:15

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('microsite', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Inspection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('unique_id', models.UUIDField(blank=True, null=True)),
                ('inspection_date_time', models.DateTimeField(blank=True, null=True)),
                ('farmer_name', models.CharField(blank=True, max_length=100, null=True)),
                ('village', models.CharField(blank=True, max_length=100, null=True)),
                ('block', models.CharField(blank=True, max_length=100, null=True)),
                ('location_name', models.CharField(blank=True, max_length=100, null=True)),
                ('warehouse_name', models.CharField(blank=True, max_length=100, null=True)),
                ('contact_number', models.CharField(blank=True, max_length=100, null=True)),
                ('mandal_name', models.CharField(blank=True, max_length=100, null=True)),
                ('buyer_name', models.CharField(blank=True, max_length=100, null=True)),
                ('grade', models.CharField(blank=True, max_length=100, null=True)),
                ('quantity_kg', models.CharField(blank=True, max_length=100, null=True)),
                ('analysis', models.JSONField(blank=True, null=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
            ],
        ),
    ]
