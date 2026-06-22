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

    raw_lf = pl.read_database_uri(
        query=query, uri="sqlite:///cell-count.db", engine="adbc"
    ).lazy()

    lf = (
        raw_lf.with_columns(total_count=pl.sum_horizontal(*cell_types))
        .with_columns([pl.col(name=col) * 100 / pl.col(name="total_count") for col in cell_types])
        .unpivot(
            index=["sample", "total_count"],
            variable_name="population",
            value_name="percentage",
            on=cell_types,
        )
        .join(
            other=raw_lf.unpivot(
                index="sample",
                variable_name="population",
                value_name="count",
                on=cell_types,
            ),
            on=["sample", "population"],
        )
        .select(["sample", "total_count", "population", "count", "percentage"])
        .sort(by="sample")
    )

    df = lf.collect()
    assert df.get_column("total_count").gt(0).all(), "found sample(s) with total_count <= 0"

    print(df)
    df.write_parquet(file=OUTFILE, mkdir=True)
    df.write_csv(OUTFILE.with_suffix(suffix=".csv"))


if __name__ == "__main__":
    main()
