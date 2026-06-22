#!/usr/bin/env python

import polars as pl
from pathlib import Path

DB_URI = "sqlite:///cell-count.db"
OUTFILE = Path("outputs") / "2-initial-analysis-results.parquet"


def main():
    cell_types = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]

    query = f"""
    SELECT sample, {", ".join(cell_types)}
    FROM samples
    """

    lf = pl.read_database_uri(
        query=query, uri="sqlite:///cell-count.db", engine="adbc"
    ).lazy()

    lf = (
        lf.with_columns(total_count=pl.sum_horizontal(*cell_types))  # pyright: ignore[reportUnknownMemberType]
        .with_columns([pl.col(col) * 100 / pl.col("total_count") for col in cell_types])
        .unpivot(
            index=["sample", "total_count"],
            variable_name="population",
            value_name="percentage",
            on=list(cell_types),
        )
        .join(
            lf.unpivot(
                index="sample",
                variable_name="population",
                value_name="count",
                on=cell_types,
            ),
            on=["sample", "population"],
        )
        .select(["sample", "total_count", "population", "count", "percentage"])
        .sort("sample")
    )

    df = lf.collect()
    df.write_parquet(file=OUTFILE, mkdir=True)
    df.write_csv(OUTFILE.with_suffix(".csv"))


if __name__ == "__main__":
    main()
