from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0003_userprofile"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenant",
            name="domain",
            field=models.CharField(blank=True, max_length=255, null=True, unique=True),
        ),
    ]
