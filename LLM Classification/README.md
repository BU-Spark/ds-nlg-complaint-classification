# LLM Classification

Uses an LLM to read every complaint narrative and code what it describes: the allegations, how severe the conduct is, how confident the model is, and any language flags. One prompt does all of it. The model never sees BPD's labels or outcomes, so its coding can be compared to BPD's afterward.

## Full run

| | |
|---|---|
| Data | `Joining Datasets/Data/data for llm/llm_final_df.csv` (3,113 cases) |
| Model | Claude Sonnet 5.5 through OpenRouter |
| Cases per call | 15 |
| Settings | temperature 0, reasoning off |
| Prompt version | `402f60b2` |
| Cost | $5.88 |

Results by severity level:

| Level | Cases |
|---|---|
| 1 (administrative) | 806 |
| 2 (non-physical misconduct) | 1,552 |
| 3 (physical contact or force) | 629 |
| Unclear | 126 |

Notes:
1. 27 narratives were too short to code (fewer than 5 real words), so they were not sent and are marked UNCLEAR.
2. 25 cases are flagged "quote not in narrative". 24 of them are near-exact quotes where the model fixed a typo or dropped a word. 1 is a paraphrase.
3. The model's answers have not been checked against human coding yet.

## How to run it

1. Open the notebook from inside this folder. It reads the data from `../Joining Datasets/Data/data for llm/`.
2. Run cell 1. It asks for the OpenRouter API key in a hidden box. **Never paste the key into a cell.**
3. Run cells 2 to 4. Cell 3 should print `3113 cases loaded, 27 too short to send`.
4. Run cell 5 to test one case, then cell 6 for the full run. If it stops partway, run cell 6 again. It skips cases that are already done.
5. Before committing, clear all outputs.

Changing the prompt changes the version number, so new results never mix with old ones.

Cell 6 saves the results as results_llm_final_df_prompt402f60b2.csv. The file here is that output renamed to results_llm_final_df.csv, with 3 minor cleanups made after the run: confidence blanked for UNCLEAR cases, only the first 3 allegations kept (2 cases had 4), and language tags sorted in P, V, G order.

## Columns

| Column | Meaning |
|---|---|
| `ia_no` | Case number |
| `run` | Model and cases per call |
| `alg` | Allegation codes, 1 to 3 (the list is in the prompt) |
| `alg_names` | Allegation names, separated by `\|` |
| `sev` | Severity sublevel, 1.1 to 3.3, or UNCLEAR when no conduct is described |
| `conf` | 1 to 5, how clearly the narrative describes the conduct. Blank for UNCLEAR. |
| `lang` | P = procedural or form-like wording, V = vague or minimized, G = garbled, cut off, or repeated |
| `quote` | The words from the narrative the model based its coding on |
| `problems` | Anything the automatic checks caught |
| `prompt_version` | Which prompt produced the row |
