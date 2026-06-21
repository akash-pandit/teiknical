#!/usr/bin/env python

import adbc_driver_sqlite.dbapi as sqlite_adbc
import logging
from pathlib import Path
import polars as pl

from adbc_driver_sqlite.dbapi import Connection

logger = logging.getLogger(Path(__file__).name)

# I/O constants
INPUT_FILE = Path("cell-count.csv")
LOGFILE = Path("load_data.log")
DB_FILENAME = "cell-count.db"

# DB constants
CONSTRAINT_FIELDS = ["condition", "treatment", "sample_type"]
SUBJECT_FIELDS = [
    "subject",
    "project",
    "condition",
    "age",
    "sex",
    "treatment",
    "response",
]
SAMPLE_FIELDS = [
    "sample",
    "subject",
    "sample_type",
    "time_from_treatment_start",
    "b_cell",
    "cd8_t_cell",
    "cd4_t_cell",
    "nk_cell",
    "monocyte",
]


def init_db_connection(uri: str, constraint_fields: list[str]) -> Connection:
    conn = sqlite_adbc.connect(uri)  # pyright: ignore[reportUnknownMemberType]
    cur = conn.cursor()

    # foreign key validation must be enabled per connection
    _ = cur.execute("PRAGMA foreign_keys = ON;")  # pyright: ignore[reportUnknownMemberType]

    # create tables for constraints expected to grow w/ the db
    for field in constraint_fields:
        _ = cur.execute(  # pyright: ignore[reportUnknownMemberType]
            f"CREATE TABLE IF NOT EXISTS {field}_ref (name TEXT PRIMARY KEY);"
        )

    # create data tables
    _ = cur.execute(  # pyright: ignore[reportUnknownMemberType]
        """  
        CREATE TABLE IF NOT EXISTS subjects (
            subject TEXT PRIMARY KEY CHECK (subject LIKE 'sbj%'),
            project TEXT NOT NULL CHECK (project LIKE 'prj%'),
            condition TEXT NOT NULL REFERENCES condition_ref(name),
            age INTEGER NOT NULL CHECK (age >= 0),
            sex TEXT NOT NULL CHECK (sex IN ('M', 'F', 'unknown')),
            treatment TEXT NOT NULL REFERENCES treatment_ref(name),
            response TEXT CHECK (
                (treatment = 'none' AND response IS NULL)
                OR (treatment != 'none' AND response IN ('yes', 'no'))
            )
        )
    """
    )

    _ = cur.execute(  # pyright: ignore[reportUnknownMemberType]
        """
        CREATE TABLE IF NOT EXISTS samples (
            sample TEXT PRIMARY KEY CHECK (sample LIKE 'sample%'),
            subject TEXT NOT NULL REFERENCES subjects(subject),
            sample_type TEXT NOT NULL REFERENCES sample_type_ref(name),
            time_from_treatment_start INTEGER NOT NULL CHECK (time_from_treatment_start >= 0),
            b_cell INTEGER NOT NULL CHECK (b_cell >= 0),
            cd8_t_cell INTEGER NOT NULL CHECK (cd8_t_cell >= 0),
            cd4_t_cell INTEGER NOT NULL CHECK (cd4_t_cell >= 0),
            nk_cell INTEGER NOT NULL CHECK (nk_cell >= 0),
            monocyte INTEGER NOT NULL CHECK (monocyte >= 0)
        )
        """
    )
    cur.close()
    conn.commit()

    return conn


def main() -> None:
    logger.info("Parsing input file")
    lf = pl.scan_csv(source=INPUT_FILE, separator=",")

    samples_iter = (
        lf.select(*SAMPLE_FIELDS)  # pyright: ignore[reportUnknownMemberType]
        .unique()
        .collect_batches()
    )

    subjects_iter = (
        lf.select(*SUBJECT_FIELDS)  # pyright: ignore[reportUnknownMemberType]
        .unique()
        .collect_batches()
    )

    conn = init_db_connection(uri=DB_FILENAME, constraint_fields=CONSTRAINT_FIELDS)

    # set up constraint field tables
    for field in CONSTRAINT_FIELDS:
        _ = (
            lf.select(field)  # pyright: ignore[reportUnknownMemberType]
            .unique()
            .rename({field: "name"})
            .collect()
            .write_database(
                table_name=f"{field}_ref",
                connection=conn,
                if_table_exists="append",
                engine="adbc",
            )
        )

    logger.info(f"Writing samples to {DB_FILENAME}")
    for samples_batch in samples_iter:
        _ = samples_batch.write_database(  # pyright: ignore[reportUnknownMemberType]
            table_name="samples",
            connection=conn,
            if_table_exists="append",
            engine="adbc",
        )

    logger.info(f"Writing subjects to {DB_FILENAME}")
    for subjects_batch in subjects_iter:
        _ = subjects_batch.write_database(  # pyright: ignore[reportUnknownMemberType]
            table_name="subjects",
            connection=conn,
            if_table_exists="append",
            engine="adbc",
        )


if __name__ == "__main__":
    logging.basicConfig(filename=LOGFILE, level=logging.INFO)
    main()
    logger.info("Done")