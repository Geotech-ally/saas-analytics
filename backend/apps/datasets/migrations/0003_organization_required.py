from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("datasets", "0002_org_scoped_upload_path"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dataset",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="datasets",
                to="organizations.organization",
            ),
        ),
    ]
