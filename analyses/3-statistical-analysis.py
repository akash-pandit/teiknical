#!/usr/bin/env python

import polars as pl
import plotly.express as px  # pyright: ignore[reportMissingTypeStubs]
from scipy.stats import mannwhitneyu  # pyright: ignore[reportUnknownVariableType, reportMissingTypeStubs]
from statsmodels.stats.multitest import multipletests  # pyright: ignore[reportUnknownVariableType, reportMissingTypeStubs]


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
        sbj.condition = 'melanoma'
        AND sbj.treatment = 'miraclib'
        AND smpl.sample_type = 'PBMC'
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
        .replace("Nk", "NK")
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
        # points="all",  #
    )

    fig.write_html(f"outputs/3-boxplot-{cell_type.replace('_', '-')}.html")  # pyright: ignore[reportUnknownMemberType]
    return fig


def compute_statistics(
    df: pl.DataFrame, cell_types: list[str]
) -> pl.DataFrame:
    resp_col = pl.col("response")
    ct_col = pl.col("population")
    t_col = pl.col("time_from_treatment_start")

    timepoints: list[int] = sorted(
        df.get_column("time_from_treatment_start").unique().to_list()
    )

    records = []

    for ct in cell_types:
        df_ct = df.filter(ct_col == ct)
        for t in timepoints:
            data_no_resp = (
                df_ct.filter((resp_col == "no") & (t_col == t))
                .get_column("percentage")
                .to_numpy()
            )
            data_yes_resp = (
                df_ct.filter((resp_col == "yes") & (t_col == t))
                .get_column("percentage")
                .to_numpy()
            )
            mwu_res = mannwhitneyu(data_no_resp, data_yes_resp)
            records.append(  # pyright: ignore[reportUnknownMemberType]
                {
                    "population": ct,
                    "time_from_treatment_start": t,
                    "p_value": float(mwu_res.pvalue),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType, reportAttributeAccessIssue]
                }
            )

    results_df = pl.DataFrame(records)  # pyright: ignore[reportUnknownArgumentType]

    _, adjusted, _, _ = multipletests(  # pyright: ignore[reportUnknownVariableType, reportAny]
        results_df.get_column("p_value").to_numpy(), method="fdr_bh", alpha=0.05
    )

    return results_df.with_columns(p_adj=pl.Series(adjusted))  # pyright: ignore[reportUnknownArgumentType]


def main():
    DB_URI = "sqlite:///cell-count.db"
    cell_types = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]

    df = get_cell_counts(db_uri=DB_URI)

    for cell_type in cell_types:
        _ = generate_plot(df, cell_type)

    stats = compute_statistics(df, cell_types)

    stats.write_csv("outputs/3-stats.csv")

    sig_stats = stats.filter(pl.col("p_adj") <= 0.05)

    sig_stats.write_csv("outputs/3-sig-stats.csv")

    print("Statistically significant samples via Benjamini-Hochberg adjusted p-values (p <= 0.05) for miraclib-treated melanoma patients:")
    print(sig_stats)


if __name__ == "__main__":
    main()
