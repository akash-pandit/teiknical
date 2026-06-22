#!/usr/bin/env python

import polars as pl
import plotly.express as px  # pyright: ignore[reportMissingTypeStubs]


def get_cell_counts(db_uri: str) -> pl.DataFrame:
    query = """
    SELECT 
        smpl.sample, sbj.response, smpl.time_from_treatment_start
    FROM 
        samples AS smpl
    JOIN 
        subjects AS sbj 
    ON 
        smpl.subject = sbj.subject
    WHERE 
        sbj.condition = "melanoma"
        AND sbj.treatment = "miraclib"
        AND smpl.sample_type = "PBMC"
    """
    treatments = pl.read_database_uri(query=query, uri=db_uri, engine="adbc")
    return pl.read_parquet(
        source="outputs/2-initial-analysis-results.parquet",
        columns=["sample", "population", "percentage"],
    ).join(other=treatments, on="sample")


def generate_plot(df: pl.DataFrame, cell_type: str):
    df = df.filter(pl.col("population") == cell_type)

    cell_type_prettified = (
        " ".join([w.capitalize() for w in cell_type.split("_")])
        .replace("Cd", "CD")
        .replace("T C", "T-C")
    )

    fig = px.box(  # pyright: ignore[reportUnknownMemberType]
        df,
        x="time_from_treatment_start",
        y="percentage",
        color="response",
        title=f"{cell_type_prettified} Relative Count Frequencies of Miraclib-Treated Melanoma Patients",
        labels={
            "percentage": "Relative Frequency (%)",
            "time_from_treatment_start": "Elapsed Time Since Treatment (days)",
            "response": "Patient Responded to Miraclib",
        },
    )

    fig.write_html(f"outputs/3-boxplot-{cell_type.replace("_", "-")}.html")  # pyright: ignore[reportUnknownMemberType]
    return fig


def main():
    DB_URI = "sqlite:///cell-count.db"
    cell_types = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]

    df = get_cell_counts(db_uri=DB_URI)

    cell_type = cell_types[1]

    for cell_type in cell_types:
        _ = generate_plot(df, cell_type)


if __name__ == "__main__":
    main()
