# Generated by Django 2.0.1 on 2018-01-17 21:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('unitime', '0005_auto_20180117_2158'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lecture',
            name='description',
            field=models.CharField(blank=True, max_length=254),
        ),
        migrations.AlterField(
            model_name='lecture',
            name='info',
            field=models.CharField(blank=True, max_length=254),
        ),
    ]
