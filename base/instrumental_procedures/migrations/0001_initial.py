# Generated by Django 5.2.3 on 2025-07-03 18:20

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='InstrumentalProcedureDefinition',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True, verbose_name='Название инструментального исследования')),
                ('description', models.TextField(blank=True, null=True, verbose_name='Описание')),
            ],
            options={
                'verbose_name': 'Инструментальное исследование (определение)',
                'verbose_name_plural': 'Инструментальные исследования (определения)',
                'ordering': ['name'],
            },
        ),
    ]
