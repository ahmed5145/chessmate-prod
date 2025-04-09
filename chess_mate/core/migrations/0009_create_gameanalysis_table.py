# Generated manually to fix missing gameanalysis table

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_alter_gameanalysis_options_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='GameAnalysis',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('accuracy_white', models.FloatField(blank=True, null=True)),
                ('accuracy_black', models.FloatField(blank=True, null=True)),
                ('analysis_data', models.JSONField(blank=True, default=dict)),
                ('feedback', models.TextField(blank=True, null=True)),
                ('game', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='gameanalysis', to='core.game')),
            ],
            options={
                'verbose_name': 'Game Analysis',
                'verbose_name_plural': 'Game Analyses',
            },
        ),
        migrations.AddIndex(
            model_name='gameanalysis',
            index=models.Index(fields=['game'], name='core_gameana_game_id_fef33f_idx'),
        ),
        migrations.AddIndex(
            model_name='gameanalysis',
            index=models.Index(fields=['created_at'], name='core_gameana_created_a7d04f_idx'),
        ),
    ] 