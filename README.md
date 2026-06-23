# Teiknical Submission

Akash Pandit's submission for Teiko's technical assessment for their Bioinformatics Engineer position.

**Table of Contents**
- [Quickstart](#quickstart)
    - [Dashboard Link](#dashboard-link)
- [Data Table Schemas](#data-table-schemas)
    - [Subjects](#subjects)
    - [Samples](#samples)
    - [Reference Tables](#reference-tables)
- [Code Overview](#code-overview)
    - [Repository Structure](#repository-structure)
    - [Part 1: Data Loading](#part-1-data-loading)
    - [Part 2: Initial Analysis](#part-2-initial-analysis)
    - [Part 3: Statistical Analysis](#part-3-statistical-analysis)
    - [Part 4: Subset Analysis](#part-4-subset-analysis)
    - [Interactive Dashboard](#interactive-dashboard)

## Quickstart

```bash
make setup  # installs uv package manager (if not present) and python dependencies

make pipeline  # runs parts 1 through 4 of the assessment in sequence

make dashboard  # starts dashboard
```
### Dashboard Link

After running `make dashboard`, the dashboard should automatically open in your default browser. If not, navigate to [`http://localhost:8501`](http://localhost:8501) while `make dashboard` is running.


## Data Table Schemas

The database was split into two data tables, one describing sample-level data (cell counts, sample type, etc.) and one describing subject-level data (e.g. age, sex). Constraints were inferred by the nature of the data (ex. counts and ages should never be negative) and observed conventions in the dataset (ex. pattern matching for samples, subjects, and projects). Certain constraints are considered dynamic (e.g. what condition a subject has, what treatment was applied) and such uses a seperate reference table with a single `name` column to hold possible values. These tables can be updated with new acceptable values without having to reconstruct the entire database, as SQLite cannot update existing CHECK statements. Including a constraint table also allows for easy identification and exclusion of typos (both would appear on initial database construction). 

> ![IMPORTANT]
> Some csv entries (treatment and response) are ambiguous on whether they are subject- or sample-level descriptors. Both entries had no effect on unique rows when in/excluded from the Subjects table, and are thus assumed to be subject-level identifiers for this exercise.

On scaling, splitting subjects and samples minimizes redundant information (Subjects has 1/3 the row count of Samples in this toy dataset), and with the inclusion of more projects and associated metadata, provides a convention to split project-specific data into its own table and update Subjects.project with a foreign key mapping to that table. While the subject, project, and sample fields follow a zero-left-padded naming convention to standardize length, as the database scales the padding length would change, and as such the zero padding size was not included in the schema. 

### Subjects 
| column | type | constraints | inferred description | 
| --- | --- | --- | --- | 
| subject | Text | Primary Key, like `sbj*` | subject (sample source) unique identifier |
| project | Text | Not null, like `prj*` | project (that subject was sampled for) unique identifier |
| condition | Text | Foreign key for condition reference table | subject disease name or `healthy` for control |
| age | Integer | Not null, >= 0 | subject age |
| sex | Text | Not null, in `{'M', 'F', 'unknown'}` | subject biological sex |
| treatment | Text | Foreign key for treatment reference table | drug name administered to subject or `none` |
| response | Text | Null if treatment is `'none'`, else `'yes'`/`'no'` | whether subject responded to drug or null if N/A |

### Samples
| column | type | constraints | inferred description |
| --- | --- | --- | --- |
| sample | Text | Primary Key, like `` | sample unique identifier |
| subject | Text | Foreign key for subjects table | unique identifier of sampled subject |
| sample_type | Text | Foreign key for cell type reference table | sample type (whether sample came from PBMCs or whole blood) |
| time_from_treatment_start | Integer | Not null, >= 0 | number of days elapsed at sampling time from when treatment began |
| b_cell | Integer | Not null, >= 0 | B-cell count in sample |
| cd8_t_cell | Integer | Not null, >= 0 | CD8+ T-cell count in sample |
| cd4_t_cell | Integer | Not null, >= 0 | CD4+ T-cell count in sample |
| nk_cell | Integer | Not null, >= 0 | Natural killer cell count in sample |
| monocyte | Integer | Not null, >= 0 | Monocyte count in sample |\

### Reference Tables
| table name | `name` column type | `name` column constraints | `name` column values |
| --- | --- | --- | --- |
| condition_ref | Text | Primary key | `melanoma`, `carcinoma`, `healthy` |
| sample_type_ref | Text | Primary key | `PBMC`, `WB` |
| treatment_ref | Text | Primary key | `phauximab`, `miraclib`, `none` |

## Code Overview

### Repository Structure

`load_data.py` was kept in the root directory by project specification, and `app.py` followed suit. Analysis scripts were separated out to their own directory for organization and prepended with which part they addressed (e.g. Part 2 -> `2-initial-analysis.py`). Analysis output files/figures were saved in `outputs/`. As they are all rendered by the dashboard, `outputs/` also serves as a data/assets directory for said dashboard. 

As each analysis step could efficiently run in-sequence without any need for parallelization (other than what polars' and SQLite's engines provide), each part was contained to its own python script, each run in-line. Resulting tables were written to standard output in pipeline execution and saved as csvs/parquet files for dashboard rendering.

### Part 1: Data Loading

The initial data loading script was designed with speed in mind, using polars with the Arrow Database Connection backend. Unlike pandas, polars provides native multithreading support and a strict type system which pays dividends in speed and efficiency. For arbitrarily large input files, polars lazy loading (LazyFrames) and chunking prevent out-of-memory errors (actually pretty helpful for my 8GB RAM laptop) in both reading and writing. 

### Part 2: Initial Analysis

Initial analysis makes use of polars' LazyFrames for efficient transformations and writes to a parquet file for efficient storage and quick rendering by the dashboard. 

### Part 3: Statistical Analysis

Part 3 is the heavyweight of this analysis. Comparisons were done between responder groups given both a particular cell population and time since treatment. Mixing observations by day, especially with sampling times each separated by a week, would have otherwise introduced a serious confounder. Time observations are intuitive to compare given a cell type, thus the yes/no comparisons for each time point were left on the same figure, where different figures can be selected via cell type dropdown to prevent visual clutter.

Even with hundreds of samples per compared condition, significance tests were performed with a Mann-Whitney U Test as sampling distribution means could still cluster against the set 0 or 100% boundaries, and is similar enough in power to a Student's T-Test to avoid statistical power-based concerns.

Figures were generated as plotly-based JSON files to easily render in the dashboard and provide interactivity (hovering over a boxplot to see the IQR and other median-based statistics, zooming in to specific regions, etc.), while also enabling dashboard viewers to save a figure as a png.

### Part 4: Subset Analysis

Part 4 queries the database generated in Part 1 to render all PBMC samples taken at baseline (t=0) from miraclib-treated melanoma patients via polars, with results saved to a csv. Further queries are performed through polars and also saved to csvs for dashboard rendering.

### Interactive Dashboard

The dashboard (`app.py`) is built on Streamlit, a lightweight Python framework designed specifically to generate dashboards and data-based web apps. Each part is split into its own tab on the dashboard, with interactive tables and plotly figures.
