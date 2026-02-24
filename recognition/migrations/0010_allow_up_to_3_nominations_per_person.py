# Allow up to 3 nominations per person per session

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("recognition", "0009_remove_winner_name"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="nomination",
            name="one_nomination_per_person_per_session",
        ),
    ]
