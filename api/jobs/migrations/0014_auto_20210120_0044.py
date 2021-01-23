# Generated by Django 3.1 on 2021-01-20 00:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0013_auto_20201107_2201'),
    ]

    operations = [
        migrations.AddField(
            model_name='occupationtransitions',
            name='total_transition_obs',
            field=models.DecimalField(decimal_places=5, max_digits=20, null=True),
        ),
        migrations.AlterField(
            model_name='occupationtransitions',
            name='soc1',
            field=models.CharField(max_length=7, null=True),
        ),
        migrations.AlterField(
            model_name='occupationtransitions',
            name='soc2',
            field=models.CharField(max_length=7, null=True),
        ),
    ]
