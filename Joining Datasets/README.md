# Complaint Data Joining

## Overview
The Joining Datasets folder is used to clean and merge files for 2011-2020, 2019 and 2020-2026 into one dataset. 2019 and 2020-2026 datasets are cleaned individually. Column names are standardized, rows are exploded and necessary years are isolated. Then we cleaned merged the data, standardizes allegation labels, collapses the data to one row per case, and creates the files used for the LLM coding pass.

## Repository setup

### Top-level

- `exploding_2020_2026.ipynb`: cleans and explodes 2020-2026 dataset
- `cleaning_2019_data.ipynb`: cleans 2019 data and isolates it from the other years that are already included in the 2011-2020 dataset.
- `joining.ipynb`: Joins 2011-2020, 2019 and 2020-2026 data to create one comprehensive dataset, as well as isolating the narrative which we will be using for our LLM pass. 


The notebooks reads and writes files in a `Data/` folder that is also in the `Joining Datasets\` folder to the notebook. The following three files need to be in the `Data/` folder and there needs to be an empty `data for llm/` folder that the llm data can be saved in before running:

-  `iad_extracted_with_youth_labels_scrubbed.csv`: IAD complaints, 2011-2020 (2020 cases are split out and handled separately in joining notebook)
-  `Mikaela McSharry MuckRock B2026-519.xlsx`: most recent data for 2020-2026
- `COMPLAINTS CONVERTED - 2016,17,19,20_corrected_file_final-Spark-spring2024 (1).xlsx`: Data used to extract 2019 complaints.

## What each notebook does

#### `exploding_202_2026.ipynb`
1. **explode the rows** so that each row is a unique combination of allegation and narrative
2. **reformated narrative column** to cleanly convert to a csv 
3. **standardized column names** to fit column names in 2011-2020.
#### `cleaning_2019_data.impyb`
1. **selected 2019 rows** and removed all other rows
2. **reformated narrative column** to cleanly convert to a csv 
3. **standardized column names** to fit column names in 2011-2020 and 2020-2026 data. 
#### `Joining.ipynb`
1. **Handle 2020 cases** to make sure there is no duplicate rows as 2020 is included in both 2011-2020 and 2020-2026 but not all rows are included in both
2. **Cleaning**: removing duplicates and rows without values in the allegations, narrative or ia_no columns
4. **Standardize allegation labels.** standardizing allegations for analysis and categorization. (for more information look at Notes section)
6. **Collapse to one row per case.** We want to collapse the rows in such a way that the `ia_no` is unique. We are seperating cases that have multiple allegations with ` | `. This will ease analysis later on
8. **Create the files.** Outcome, finding, disposition, officer, and category columns are removed. The LLM sees only the case ID and the narrative, so coding is blind to findings and dispositions.

## Output files

All outputs are written to `Data/` and `data for llm/`.

| File | Description |
| --- | --- |
| `cleaned_complaints_2019.csv` | All 2019 complaints cleaned and standardized|
 | `2020_2026_exploded.csv` | 2020-2026 complaints exploded, cleaned and standardized|
| `complaints_combined_deduped.csv` | All complaint rows after combining, cleaning, and deduplication (one row per allegation) |
| `all_complaints_collapsed.csv` | One row per case, with allegations joined by ` | ` |
| `sample_complaints.csv` | 15-case sample of the collapsed data, with all columns |
| `llm_final_df.json` / `.csv` | Full dataset for the LLM pass (case ID and narrative only) |
| `sample_complaints_llm.json` / `.csv` | 15-case sample for the LLM pass (case ID and narrative only) |


## How to run

Open the `Joining Datasets/` folder in VS Code and make sure that all of the necessary files are in the `Data/` folder. Then run the notebooks in the following order: `cleaning_2019_data.ipynb` then `exploding_2020_2026.ipynb` and after the other two run `joining.ipynb`.


## Requirements

- Python 3.9 or newer
- pandas

Install pandas with:

```
pip install pandas
```

## Notes

- Allegation labels are standardized for analysis, but the original `allegation_x` still included as reference. We are standardizing the allegations because there is many that have the same meaning but the officer has multiple counts of this allegation. This is irrelevant for analysis and the llm would not be able to predict those
- the dataset 2011-2020 does not include 2019 so we are merging that seperatly
- we are removing all instances of 2020 in the 2011-2020 data and then addressing them one at a time because the 2020-2026 data includes some but not all of the complaints found in the 2011-2020 dataset.