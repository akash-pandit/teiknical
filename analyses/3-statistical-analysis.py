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
        # points="all",  #
    )

    fig.write_html(f"outputs/3-boxplot-{cell_type.replace('_', '-')}.html")  # pyright: ignore[reportUnknownMemberType]
    return fig


def compute_statistics(
    df: pl.DataFrame, cell_types: list[str]
) -> tuple[pl.DataFrame, pl.DataFrame]:
    resp_col = pl.col("response")
    ct_col = pl.col("population")
    t_col = pl.col("time_from_treatment_start")

    timepoints: list[int] = sorted(
        df.get_column("time_from_treatment_start").unique().to_list()
    )

    raw_pvalues: dict[str, list[float]] = {ct: [] for ct in cell_types}

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
            raw_pvalues[ct].append(float(mwu_res.pvalue))  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType, reportAttributeAccessIssue]

    raw_df = pl.DataFrame(raw_pvalues).with_columns(
        time_from_treatment_start=pl.Series(timepoints)
    )

    # flatten all p-values across cell types + timepoints for a single FDR correction pass
    flat_pvals = [p for ct in cell_types for p in raw_pvalues[ct]]
    _, adjusted_flat, _, _ = multipletests(flat_pvals, method="fdr_bh", alpha=0.05)  # pyright: ignore[reportUnknownVariableType, reportAny]

    # reshape back into per-cell-type lists, same order as raw_pvalues was built
    adjusted_pvalues: dict[str, list[float]] = {ct: [] for ct in cell_types}
    idx = 0
    for ct in cell_types:
        n = len(timepoints)
        adjusted_pvalues[ct] = list(adjusted_flat[idx : idx + n])  # pyright: ignore[reportUnknownArgumentType]
        idx += n

    adj_df = pl.DataFrame(adjusted_pvalues).with_columns(
        time_from_treatment_start=pl.Series(timepoints)
    )

    return raw_df, adj_df


def main():
    DB_URI = "sqlite:///cell-count.db"
    cell_types = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]
    
    df = get_cell_counts(db_uri=DB_URI)

    for cell_type in cell_types:
        _ = generate_plot(df, cell_type)

    raw, adj = compute_statistics(df, cell_types)

    raw.write_csv("outputs/3-stats-raw.csv")
    adj.write_csv("outputs/3-stats-adj.csv")


if __name__ == "__main__":
    main()
