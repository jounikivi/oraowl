# oraw_app/migrations/0018_remove_split_uniq_split_result_seq_and_more.py
# Reordered so that data cleanup runs BEFORE NOT NULL / UNIQUE constraints.

from __future__ import annotations

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


def forwards_clean_splits(apps, schema_editor):
    """
    Siivoa data ennen skeeman kiristystä:
      - control_code: NULL tai "" -> "UNKNOWN"
      - split_time_s: NULL -> 0
      - seq: NULL -> 0 (varmistus)
      - deduplikoi (result_id, control_code): säilytä pienin id
    """
    Split = apps.get_model("oraw_app", "Split")
    db = schema_editor.connection.alias

    # Täytä puuttuvat/tyhjät control_codet ja ajat
    Split.objects.using(db).filter(control_code__isnull=True).update(control_code="UNKNOWN")
    Split.objects.using(db).filter(control_code="").update(control_code="UNKNOWN")
    Split.objects.using(db).filter(split_time_s__isnull=True).update(split_time_s=0)
    Split.objects.using(db).filter(seq__isnull=True).update(seq=0)

    # Deduplikoi (result, control_code)
    from collections import defaultdict

    ids_by_pair = defaultdict(list)
    qs = Split.objects.using(db).only("id", "result_id", "control_code").order_by("id")
    for s in qs:
        ids_by_pair[(s.result_id, s.control_code)].append(s.id)

    to_delete = []
    for _, id_list in ids_by_pair.items():
        if len(id_list) > 1:
            # jätä ensimmäinen (pienin id), poista loput
            to_delete.extend(id_list[1:])

    if to_delete:
        Split.objects.using(db).filter(id__in=to_delete).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("oraw_app", "0017_remove_controlcard_uniq_controlcard_vendor_uid_and_more"),
    ]

    operations = [
        # Poista vanha constraint jos on olemassa (oli nimetynään aiemmin näin)
        migrations.RemoveConstraint(
            model_name="split",
            name="uniq_split_result_seq",
        ),

        # Poista vanhat kentät
        migrations.RemoveField(
            model_name="split",
            name="leg_time_s",
        ),
        migrations.RemoveField(
            model_name="split",
            name="note",
        ),
        migrations.RemoveField(
            model_name="split",
            name="time_s",
        ),

        # Lisää uudet/korvattavat kentät (annetaan defaultit jotta SQLite selviää taulun uudelleenrakennuksesta)
        migrations.AddField(
            model_name="split",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="split",
            name="cum_time_s",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="split",
            name="notes",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="split",
            name="split_time_s",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="split",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),

        # *** TÄRKEÄÄ: PUHDISTA DATA ENNEN NOT NULL / UNIQUE -MUUTOKSIA ***
        migrations.RunPython(forwards_clean_splits, migrations.RunPython.noop),

        # Nyt vasta kiristetään skeemaa
        migrations.AlterField(
            model_name="split",
            name="control_code",
            field=models.CharField(max_length=12),
        ),
        migrations.AlterField(
            model_name="split",
            name="result",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="splits",
                to="oraw_app.result",
            ),
        ),
        migrations.AlterField(
            model_name="split",
            name="seq",
            field=models.PositiveIntegerField(),
        ),

        # UNIQUE-rajoitteet vasta lopuksi (datan ollessa jo deduplikoitu)
        migrations.AddConstraint(
            model_name="split",
            constraint=models.UniqueConstraint(
                fields=("result", "seq"), name="uniq_split_per_result_seq"
            ),
        ),
        migrations.AddConstraint(
            model_name="split",
            constraint=models.UniqueConstraint(
                fields=("result", "control_code"), name="uniq_split_per_result_code"
            ),
        ),
    ]
