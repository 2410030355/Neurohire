from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Candidate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('email', models.EmailField(blank=True, max_length=254, null=True)),
                ('phone', models.CharField(blank=True, max_length=20, null=True)),
                ('resume_url', models.URLField(blank=True, null=True)),
                ('source', models.CharField(blank=True, choices=[('resume_upload', 'Resume Upload'), ('github_search', 'GitHub Search'), ('job_portal_search', 'Job Portal Search')], max_length=50, null=True)),
                ('status', models.CharField(choices=[('new', 'New'), ('analyzed', 'Analyzed'), ('scheduled', 'Scheduled'), ('waitlisted', 'Waitlisted'), ('rejected', 'Rejected'), ('hired', 'Hired')], default='new', max_length=20)),
                ('target_role', models.CharField(blank=True, max_length=255, null=True)),
                ('consistency_score', models.FloatField(blank=True, null=True)),
                ('skill_validation_score', models.FloatField(blank=True, null=True)),
                ('learning_velocity', models.CharField(blank=True, choices=[('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High')], max_length=10, null=True)),
                ('career_trajectory', models.TextField(blank=True, null=True)),
                ('role_match_score', models.FloatField(blank=True, null=True)),
                ('final_fit', models.CharField(blank=True, choices=[('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High')], max_length=10, null=True)),
                ('explainability', models.TextField(blank=True, null=True)),
                ('skills', models.JSONField(blank=True, default=list)),
                ('experience_years', models.FloatField(blank=True, null=True)),
                ('education', models.TextField(blank=True, null=True)),
                ('github_url', models.URLField(blank=True, null=True)),
                ('repo_score', models.FloatField(blank=True, null=True)),
                ('profile_summary', models.TextField(blank=True, null=True)),
                ('resume_strength_score', models.FloatField(blank=True, null=True)),
                ('improvement_suggestions', models.JSONField(blank=True, default=list)),
                ('missing_skills', models.JSONField(blank=True, default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='JobPosting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('company', models.CharField(blank=True, max_length=255, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('requirements', models.JSONField(blank=True, default=list)),
                ('skills_required', models.JSONField(blank=True, default=list)),
                ('experience_range', models.CharField(blank=True, max_length=100, null=True)),
                ('location', models.CharField(blank=True, max_length=255, null=True)),
                ('job_type', models.CharField(choices=[('full_time', 'Full Time'), ('part_time', 'Part Time'), ('internship', 'Internship'), ('contract', 'Contract')], default='full_time', max_length=20)),
                ('salary_range', models.CharField(blank=True, max_length=100, null=True)),
                ('apply_url', models.URLField(blank=True, null=True)),
                ('status', models.CharField(choices=[('active', 'Active'), ('closed', 'Closed'), ('draft', 'Draft')], default='active', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='MockInterview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(max_length=255)),
                ('questions', models.JSONField(blank=True, default=list)),
                ('overall_confidence', models.FloatField(blank=True, null=True)),
                ('overall_clarity', models.FloatField(blank=True, null=True)),
                ('total_filler_words', models.IntegerField(blank=True, null=True)),
                ('avg_speaking_pace', models.CharField(blank=True, max_length=50, null=True)),
                ('improvements', models.JSONField(blank=True, default=list)),
                ('status', models.CharField(choices=[('in_progress', 'In Progress'), ('completed', 'Completed')], default='in_progress', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='WaitlistEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('candidate_name', models.CharField(max_length=255)),
                ('role', models.CharField(blank=True, max_length=255, null=True)),
                ('reason', models.TextField(blank=True, null=True)),
                ('priority', models.CharField(choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], default='medium', max_length=10)),
                ('match_score', models.FloatField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('candidate', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='waitlist_entries', to='neurohire.candidate')),
            ],
        ),
        migrations.CreateModel(
            name='Interview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('candidate_name', models.CharField(max_length=255)),
                ('role', models.CharField(blank=True, max_length=255, null=True)),
                ('scheduled_date', models.DateTimeField()),
                ('interview_link', models.URLField(blank=True, null=True)),
                ('status', models.CharField(choices=[('scheduled', 'Scheduled'), ('completed', 'Completed'), ('cancelled', 'Cancelled'), ('no_show', 'No Show')], default='scheduled', max_length=20)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('candidate', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='interviews', to='neurohire.candidate')),
            ],
        ),
        migrations.CreateModel(
            name='AIDecisionLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('candidate_name', models.CharField(max_length=255)),
                ('ai_recommendation', models.CharField(choices=[('hire', 'Hire'), ('waitlist', 'Waitlist'), ('reject', 'Reject')], max_length=10)),
                ('recruiter_decision', models.CharField(choices=[('hire', 'Hire'), ('waitlist', 'Waitlist'), ('reject', 'Reject')], max_length=10)),
                ('ai_confidence', models.FloatField(blank=True, null=True)),
                ('reason', models.TextField(blank=True, null=True)),
                ('is_agreement', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('candidate', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='ai_logs', to='neurohire.candidate')),
            ],
        ),
    ]