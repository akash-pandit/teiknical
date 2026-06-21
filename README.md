# Teiknical Submission

Akash Pandit's submission for Teiko's technical assessment for their Bioinformatics Engineer position

## Quickstart

```bash
make setup  # installs uv package manager (if not present) and python dependencies

make pipeline  # runs parts 1 through 4 of the assessment in sequence

make dashboard  # starts dashboard
```

## Reference Tables

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

### Part 1: Data Loading

The initial data loading script was designed with speed in mind, using polars with the Arrow Database Connection backend. Unlike pandas, polars provides native multithreading support and a strict type system which pays dividends in speed and efficiency. For arbitrarily large input files, polars lazy loading (LazyFrames) and chunking prevent out-of-memory errors (actually pretty helpful for my 8GB RAM laptop) in both reading and writing. 

### Part 2: 