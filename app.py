#!/usr/bin/env python

from pathlib import Path

import plotly.io as pio  # pyright: ignore[reportMissingTypeStubs]
import polars as pl
import streamlit as st


OUTDIR = Path("outputs")
DB_URI = "sqlite:///cell-count.db"

CELL_TYPES = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]
CELL_TYPE_LABELS = {
    "b_cell": "B Cell",
    "cd8_t_cell": "CD8 T-Cell",
    "cd4_t_cell": "CD4 T-Cell",
    "nk_cell": "NK Cell",
    "monocyte": "Monocyte",
}

def main():
    st.set_page_config(page_title="Teiko OA", layout="wide")
    _ = st.title("Loblaw Bio Clinical Trial Data")

    tab_overview, tab_stats, tab_subset = st.tabs(
        ["Initial Analysis", "Statistical Analysis", "Subset Analysis"]
    )


    # Cached helper functions


    @st.cache_data
    def load_csv(path: Path):
        return pl.read_csv(path)

    @st.cache_data
    def load_parquet(path: Path):
        return pl.read_parquet(path)

    @st.cache_data
    def load_boxplot(cell_type: str):
        path = OUTDIR / f"3-boxplot-{cell_type.replace('_', '-')}.json"
        return pio.read_json(path)  # pyright: ignore[reportUnknownMemberType]


    # Tab 1: Initial Analysis (Part 2)


    with tab_overview:
        _ = st.header("Relative Cell Population Frequencies")
        _ = st.text(
            "Per-sample total cell counts and relative frequency (%) "
            + "for each immune cell population."
        )

        overview_df = load_parquet(OUTDIR / "2-initial-analysis-results.parquet")
        _ = st.dataframe(overview_df, width="stretch")


    # Tab 2: Statistical Analysis (Part 3)


    with tab_stats:
        _ = st.header("Responder vs. Non-Responder Comparison")
        _ = st.text(
            "Miraclib-treated melanoma patients, PBMC samples only. Boxplots "
            + "compare relative frequency by response status, stratified by "
            + "timepoint."
        )

        dropdown_col, figure_col = st.columns([1, 5])
        with dropdown_col:
            selected_label = st.selectbox(
                "Cell population", options=list(CELL_TYPE_LABELS.values()),
                width=200
            )
            selected_cell_type = next(
                ct for ct, label in CELL_TYPE_LABELS.items() if label == selected_label
            )

        with figure_col:
            try:
                fig = load_boxplot(selected_cell_type)
                _ = st.plotly_chart(fig, width="stretch")  # pyright: ignore[reportUnknownMemberType]
            except FileNotFoundError:
                _ = st.warning(
                    f"No figure found for {selected_label}. " +
                    f"Expected outputs/3-boxplot-{selected_cell_type.replace('_', '-')}.json — " +
                    "run `make pipeline` first."
                )

            _ = st.subheader("Significance Summary (FDR-corrected)")
            _ = st.caption(
                "P-values from two-sided Mann-Whitney U tests, corrected for multiple " +
                "comparisons across all population × timepoint combinations via " +
                "Benjamini-Hochberg FDR (α = 0.05)." 
            )

            stats_df = load_csv(OUTDIR / "3-stats.csv")

            significant_only = st.checkbox("Show only significant results (p_adj < 0.05)")
            display_df = (
                stats_df.filter(pl.col("p_adj") < 0.05) if significant_only else stats_df
            )
            _ = st.dataframe(display_df, width="content")


    # Tab 3: Subset Analysis (Part 4)


    with tab_subset:
        _ = st.header("Data Subset Analysis")
        _ = st.text("All PBMC samples taken at baseline (t=0) from miraclib-treated melanoma patients.")

        main_subset_df = load_csv(OUTDIR / "4-baseline-pbmc-miraclib-melanoma.csv")
        _ = st.dataframe(main_subset_df, width="stretch")

        _ = st.caption(
                "The below tables were generated from the above subset. " +
                "Any missing categories did not appear in the main subset."
        )

        per_proj_col, by_resp_col, by_sex_col = st.columns(3)

        with per_proj_col:
            _ = st.subheader("Samples per Project")
            _ = st.dataframe(load_csv(OUTDIR / "4-samples-per-project.csv"))

        with by_resp_col:
            _ = st.subheader("Subjects by Response")
            _ = st.dataframe(load_csv(OUTDIR / "4-subjects-by-resp.csv"))

        with by_sex_col:
            _ = st.subheader("Subjects by Sex")
            _ = st.dataframe(load_csv(OUTDIR / "4-subjects-by-sex.csv"))


if __name__ == "__main__":
    main()
