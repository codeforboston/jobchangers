# Generated by Django 3.1 on 2020-10-14 00:33
from django.db import migrations, models, connection
from data.scripts.sql_loader import (
    load_occupation_transitions_to_sql,
)
import logging

log = logging.getLogger()


class Migration(migrations.Migration):
    """
    Update the model to have autofield to accomodate auto-incrementing ids and nullability on soc2 field.
    Add code to migrate data from data migration script into django model.
    """

    dependencies = [
        ("jobs", "0008_auto_20201006_AddStateData"),
    ]

    def forwards_source_data(apps, schema_editor):
        with connection.schema_editor() as my_schema_editor:
            log.info(f"0009 show db {my_schema_editor.connection.alias}")
        log.info("0009 Processing data from csv; This will take a few minutes.")
        conn_info = str(schema_editor.connection.__dict__["connection"])
        log.info(f"0009 Connection Info: {conn_info}")
        db_name = conn_info.split("dbname=")[1].split(" ")[0]
        log.info(f"0009 DB Name: {db_name}")

        load_occupation_transitions_to_sql(
            "data/occupation_transitions_public_data_set.csv",
            db_name,
        )
        log.info("0009 done with forward load")

    def reverse_source_data(apps, schema_editor):
        log.info("0009 removing source data")
        migrations.RunSQL([("drop table occupation_transition")])

    def forwards_func(apps, schema_editor):
        # alter fields for go-forward work
        migrations.AlterField(
            "OccupationTransitions",
            "id",
            models.AutoField(auto_created=True, primary_key=True),
        )

    def reverse_func(apps, schema_editor):
        # alter fields for backward migration.
        migrations.AlterField(
            "OccupationTransitions", "id", models.IntegerField(primary_key=True)
        )

    # note we need to use coalesce here because django is garbage.
    # See that nullability is not handled correctly.
    operations = [
        migrations.RunPython(forwards_source_data, reverse_source_data),
        migrations.RunPython(forwards_func, reverse_func),
        migrations.RunSQL(
            sql="alter table occupation_transition add id serial",
            reverse_sql="select coalesce(null,'abc')",
        ),
        migrations.RunSQL(
            [
                (
                    "insert into jobs_occupationtransitions (id, soc1, soc2, pi) select id, soc1, coalesce(soc2,'') as soc2, transition_share from occupation_transition"
                )
            ],
            [("DELETE FROM jobs_occupationtransitions")],
        ),
    ]
