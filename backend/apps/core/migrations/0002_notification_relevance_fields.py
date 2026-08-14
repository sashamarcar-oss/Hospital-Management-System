from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="priority",
            field=models.CharField(choices=[("low", "Low"), ("normal", "Normal"), ("high", "High"), ("urgent", "Urgent")], default="normal", max_length=16),
        ),
        migrations.AddField(model_name="notification", name="related_module", field=models.CharField(blank=True, max_length=64)),
        migrations.AddField(model_name="notification", name="related_object_id", field=models.IntegerField(blank=True, null=True)),
    ]
