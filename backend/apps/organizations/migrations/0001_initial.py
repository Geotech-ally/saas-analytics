import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Organization",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("slug", models.SlugField(max_length=100, unique=True)),
                ("plan", models.CharField(
                    choices=[("free", "Free"), ("pro", "Pro"), ("enterprise", "Enterprise")],
                    default="free", max_length=20,
                )),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("max_users", models.PositiveIntegerField(default=5)),
                ("max_datasets", models.PositiveIntegerField(default=10)),
            ],
            options={"db_table": "organizations"},
        ),
        migrations.AddIndex(
            model_name="organization",
            index=models.Index(fields=["slug"], name="org_slug_idx"),
        ),
    ]
