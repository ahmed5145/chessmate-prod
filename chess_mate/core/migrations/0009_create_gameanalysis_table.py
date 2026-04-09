# Compatibility migration retained as a no-op because GameAnalysis is already
# created in the initial migration.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_alter_gameanalysis_options_and_more'),
    ]

    operations = []