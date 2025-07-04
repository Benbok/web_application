# Generated by Django 5.2.3 on 2025-07-04 14:45

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0002_remove_medication_default_dosage_and_more'),
        ('treatment_assignments', '0003_generaltreatmentassignment_cancellation_reason_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='medicationassignment',
            options={'verbose_name': 'Назначение препарата', 'verbose_name_plural': 'Назначения препаратов'},
        ),
        migrations.RemoveField(
            model_name='medicationassignment',
            name='dosage',
        ),
        migrations.RemoveField(
            model_name='medicationassignment',
            name='duration',
        ),
        migrations.RemoveField(
            model_name='medicationassignment',
            name='frequency',
        ),
        migrations.RemoveField(
            model_name='medicationassignment',
            name='route',
        ),
        migrations.AddField(
            model_name='medicationassignment',
            name='dosing_rule',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='pharmacy.dosingrule', verbose_name='Правило дозирования'),
        ),
        migrations.AlterField(
            model_name='medicationassignment',
            name='medication',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='pharmacy.medication', verbose_name='Препарат'),
        ),
    ]
