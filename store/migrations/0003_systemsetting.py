# Generated by Django 4.2.19 on 2025-02-19 22:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0002_debts'),
    ]

    operations = [
        migrations.CreateModel(
            name='SystemSetting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('store_name', models.CharField(default='Jewelry Sales Manager', max_length=100)),
                ('contact_email', models.EmailField(default='info@example.com', max_length=254)),
                ('tax_rate', models.FloatField(default=5.0, help_text='Tax rate in percentage')),
                ('discount_rate', models.FloatField(default=0.0, help_text='Default discount rate in percentage')),
            ],
        ),
    ]
