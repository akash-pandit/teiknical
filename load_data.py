#!/usr/bin/env python

import adbc_driver_sqlite.dbapi as sqlite_adbc
import logging
import polars as pl

from adbc_driver_sqlite.dbapi import Connection
from pathlib import Path
from sys import exit as sysexit

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

    # parse input data into data tables (to be sqlite tables)

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

    # set up constraint field tables

    conn = init_db_connection(uri=DB_FILENAME, constraint_fields=CONSTRAINT_FIELDS)

    for field in CONSTRAINT_FIELDS:
        values = (
            lf.select(field)  # pyright: ignore[reportUnknownMemberType]
            .unique()
            .rename({field: "name"})
            .collect()
            .get_column("name")
            .to_list()
        )
        cur = conn.cursor()
        cur.executemany(  # pyright: ignore[reportUnknownMemberType]
            f"INSERT OR IGNORE INTO {field}_ref (name) VALUES (?);",
            [(v,) for v in values],  # pyright: ignore[reportAny]
        )
        cur.close()
    conn.commit()

    # set up data tables

    data_tables = {"samples": samples_iter, "subjects": subjects_iter}

    for table_name, table_iter in data_tables.items():
        logger.info(f"Writing to table {table_name} in {DB_FILENAME}")

        cur = conn.cursor()
        _ = cur.execute(f"DROP TABLE IF EXISTS {table_name};")  # pyright: ignore[reportUnknownMemberType]
        conn.commit()

        for table_batch in table_iter:
            _ = table_batch.write_database(  # pyright: ignore[reportUnknownMemberType]
                table_name=table_name,
                connection=conn,
                if_table_exists="append",
                engine="adbc",
            )


if __name__ == "__main__":
    logging.basicConfig(filename=LOGFILE, level=logging.INFO)

    if not INPUT_FILE.is_file():
        errmsg = f"Cannot find input file {INPUT_FILE.name}, exiting..."
        logger.fatal(errmsg)
        sysexit(errmsg)

    main()
    logger.info("Done")