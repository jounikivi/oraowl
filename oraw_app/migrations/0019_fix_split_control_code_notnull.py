from __future__ import annotations

from django.db import migrations, models


def populate_control_code_and_split_time(apps, schema_editor):
    """
    Siivoa data ennen NOT NULL -kiristystä:
      - control_code: NULL tai "" -> "UNKNOWN"
      - split_time_s: NULL -> 0 (varmuuden vuoksi)
    """
    Split = apps.get_model("oraw_app", "Split")
    db = schema_editor.connection.alias

    # control_code: NULL/tyhjä -> "UNKNOWN"
    Split.objects.using(db).filter(control_code__isnull=True).update(control_code="UNKNOWN")
    Split.objects.using(db).filter(control_code="").update(control_code="UNKNOWN")

    # split_time_s: NULL -> 0 (vaikkei tämän pitäisi olla enää NULL, varmistetaan)
    Split.objects.using(db).filter(split_time_s__isnull=True).update(split_time_s=0)


class Migration(migrations.Migration):

    dependencies = [
        ("oraw_app", "0018_remove_split_uniq_split_result_seq_and_more"),
    ]

    operations = [
        migrations.RunPython(populate_control_code_and_split_time, migrations.RunPython.noop),

        # Vasta nyt kiristetään NOT NULL (SQLite tekee taulun uudelleen ja kopioi rivit)
        migrations.AlterField(
            model_name="split",
            name="control_code",
            field=models.CharField(max_length=12),
        ),
    ]