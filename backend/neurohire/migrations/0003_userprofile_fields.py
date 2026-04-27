from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('neurohire', '0002_userprofile'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='phone',
            field=models.CharField(blank=True, default='', max_length=30),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='company',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='college',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='bio',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='linkedin',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='location',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='job_title',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='aidecisionlog',
            name='role_match_score',
            field=models.FloatField(blank=True, null=True),
        ),
    ]