# Generated by Django 5.2.4 on 2025-07-13 16:41

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('patients', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Department',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Наименование отделения')),
                ('slug', models.SlugField(blank=True, unique=True, verbose_name='Код отделения (slug)')),
                ('description', models.TextField(blank=True, verbose_name='Описание')),
            ],
            options={
                'verbose_name': 'Отделение',
                'verbose_name_plural': 'Отделения',
            },
        ),
        migrations.CreateModel(
            name='PatientDepartmentStatus',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_archived', models.BooleanField(default=False, verbose_name='Архивировано')),
                ('archived_at', models.DateTimeField(blank=True, null=True, verbose_name='Дата архивации')),
                ('status', models.CharField(choices=[('pending', 'Ожидает принятия'), ('accepted', 'Принят в отделение'), ('discharged', 'Выписан из отделения'), ('transferred_out', 'Переведен в другое отделение'), ('transfer_cancelled', 'Перевод отменен')], default='pending', max_length=20, verbose_name='Статус в отделении')),
                ('admission_date', models.DateTimeField(auto_now_add=True, verbose_name='Дата поступления в отделение')),
                ('acceptance_date', models.DateTimeField(blank=True, null=True, verbose_name='Дата принятия')),
                ('discharge_date', models.DateTimeField(blank=True, null=True, verbose_name='Дата выписки')),
                ('notes', models.TextField(blank=True, verbose_name='Заметки')),
                ('accepted_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='Принят сотрудником')),
                ('department', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='patients_in_department', to='departments.department', verbose_name='Отделение')),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='department_statuses', to='patients.patient', verbose_name='Пациент')),
            ],
            options={
                'verbose_name': 'Статус пациента в отделении',
                'verbose_name_plural': 'Статусы пациентов в отделениях',
            },
        ),
    ]
