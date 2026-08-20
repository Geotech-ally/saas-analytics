import apps.datasets.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("datasets", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dataset",
            name="file",
            field=models.FileField(upload_to=apps.datasets.models.dataset_upload_path),
        ),
    ]
