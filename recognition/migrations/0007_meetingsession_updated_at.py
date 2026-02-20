# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("recognition", "0006_remove_vote_voter_alter_nomination_unique_together_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="meetingsession",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
    ]
