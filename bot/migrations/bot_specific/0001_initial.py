# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-05-08 16:19
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Bot',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=750)),
                ('token', models.CharField(max_length=200)),
                ('active', models.BooleanField(default=False)),
                ('group_text_with_location', models.BooleanField(default=True)),
                ('group_photo_with_location', models.BooleanField(default=True)),
                ('location_first', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='Segnalazione',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='TelegramMessage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('telegram_message_id', models.IntegerField()),
                ('when_sent', models.DateTimeField()),
                ('when_registered', models.DateTimeField(auto_now_add=True)),
                ('processed', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='TelegramUser',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('telegram_id', models.IntegerField()),
                ('first_name', models.CharField(default=b'', max_length=255)),
                ('last_name', models.CharField(default=b'', max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='LocationMessage',
            fields=[
                ('telegrammessage_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='bot.TelegramMessage')),
                ('longitude', models.FloatField(blank=True, null=True)),
                ('latitude', models.FloatField(blank=True, null=True)),
            ],
            bases=('bot.telegrammessage',),
        ),
        migrations.CreateModel(
            name='PhotoMessage',
            fields=[
                ('telegrammessage_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='bot.TelegramMessage')),
                ('photo_thumb', models.FileField(upload_to=b'photo/')),
                ('photo_hires', models.FileField(upload_to=b'photo/')),
                ('caption', models.CharField(default=b'', max_length=2000)),
            ],
            bases=('bot.telegrammessage',),
        ),
        migrations.CreateModel(
            name='TextMessage',
            fields=[
                ('telegrammessage_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='bot.TelegramMessage')),
                ('text', models.CharField(default=b'', max_length=2000)),
            ],
            bases=('bot.telegrammessage',),
        ),
        migrations.AddField(
            model_name='telegrammessage',
            name='bot',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bot.Bot'),
        ),
        migrations.AddField(
            model_name='telegrammessage',
            name='utente',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bot.TelegramUser'),
        ),
        migrations.AddField(
            model_name='segnalazione',
            name='location_message',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bot.TextMessage'),
        ),
        migrations.AddField(
            model_name='segnalazione',
            name='photo_message',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='segnalazione', to='bot.PhotoMessage'),
        ),
    ]
