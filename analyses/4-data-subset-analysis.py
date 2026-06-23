#!/usr/bin/env python

import polars as pl
from pathlib import Path


DB_URI = "sqlite:///cell-count.db"
DB_ENGINE = "adbc"
OUTDIR = Path("outputs")


def extend_query(df: pl.DataFrame, select_cols: list[str], groupby_col: str):
    return (
        df.select(*select_cols)
        .unique()
        .group_by(groupby_col)
        .len()
        .rename(mapping={"len": "count"})
        .sort(groupby_col)
    )


def main():
    # Queries to get initial database

    melanoma_miraclib_patients = pl.read_database_uri(
        query="""
        SELECT * 
        FROM subjects 
        WHERE condition = 'melanoma' 
        AND treatment = 'miraclib';
        """,
        uri=DB_URI,
        engine=DB_ENGINE,
    )
    baseline_pbmc_samples = pl.read_database_uri(
        query="""
        SELECT *
        FROM samples
        WHERE sample_type = 'PBMC'
        AND time_from_treatment_start = 0;
        """,
        uri=DB_URI,
        engine=DB_ENGINE,
    )

    samples = melanoma_miraclib_patients.join(
        other=baseline_pbmc_samples, on="subject", how="inner"
    ).sort("subject", "project", "sample")

    print(
        "All baseline PBMC samples from miraclib-treated melanoma patients",
        samples,
        sep="\n",
    )
    samples.write_csv(OUTDIR / "4-baseline-pbmc-miraclib-melanoma.csv")

    print("\nExtending initial query...\n")

    samples_per_project = extend_query(samples, ["project", "sample"], "project")
    samples_per_project.write_csv(OUTDIR / "4-samples-per-project.csv")
    print("Number of samples per project", samples_per_project, sep="\n")

    subjects_by_resp = extend_query(samples, ["subject", "response"], "response")
    subjects_by_resp.write_csv(OUTDIR / "4-subjects-by-resp.csv")
    print("Number of subjects per response status", subjects_by_resp, sep="\n")

    subjects_by_sex = extend_query(samples, ["subject", "sex"], "sex")
    subjects_by_sex.write_csv(OUTDIR / "4-subjects-by-sex.csv")
    print("Number of subjects by reported sex", subjects_by_sex, sep="\n")


if __name__ == "__main__":
    main()
