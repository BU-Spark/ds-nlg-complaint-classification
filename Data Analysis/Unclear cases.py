
from pathlib import Path
from collections import Counter
import re
import sys

import pandas as pd
import matplotlib.pyplot as plt



BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "combined_classification_cleaned_df.csv"
OUTPUT_DIR = BASE_DIR / "results"
TABLE_DIR = OUTPUT_DIR / "tables"
FIGURE_DIR = OUTPUT_DIR / "figures"

ID_COL = "ia_no"
BPD_COL = "allegation_standardized"
LLM_COL = "alg_names"
SEVERITY_COL = "sev"
SOURCE_COL = "incident_type_x"


LABEL_ALIASES = {}

UNMAPPED_LABELS = {"UNMAPPED", "UNMAPPED BPD ALLEGATION", "UNKNOWN", "N/A", "NA", ""}


#helpers 

def clean_label(value):
    """Normalize whitespace and apply only explicitly approved aliases."""
    label = re.sub(r"\s+", " ", str(value)).strip()
    if label.upper() in UNMAPPED_LABELS:
        return "UNMAPPED"
    return LABEL_ALIASES.get(label, label)


def split_labels(value):
    """Split pipe-separated labels into a set of normalized labels."""
    if pd.isna(value):
        return set()

    labels = set()
    for part in str(value).split("|"):
        label = clean_label(part)
        if label and label.upper() not in UNMAPPED_LABELS:
            labels.add(label)
    return labels


def save_table(data, filename):
    """Save a DataFrame as a CSV in the results/tables folder."""
    data.to_csv(TABLE_DIR / filename, index=False)


def save_bar_chart(data, label_col, value_col, title, filename,
                   horizontal=True, top_n=15):
    """Create and save a simple bar chart."""
    plot_data = data.head(top_n).copy()
    if plot_data.empty:
        return

    plt.figure(figsize=(11, max(5, len(plot_data) * 0.38)))
    if horizontal:
        plot_data = plot_data.iloc[::-1]
        plt.barh(plot_data[label_col].astype(str), plot_data[value_col])
        plt.xlabel("Number of complaints")
        plt.ylabel("")
    else:
        plt.bar(plot_data[label_col].astype(str), plot_data[value_col])
        plt.ylabel("Number of complaints")
        plt.xticks(rotation=45, ha="right")

    plt.title(title)
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / filename, dpi=200, bbox_inches="tight")
    plt.close()


def label_counts(label_sets, column_name):
    """Count how many complaints contain each label."""
    counts = Counter()
    for labels in label_sets:
        counts.update(labels)
    result = pd.DataFrame(
        [(label, count) for label, count in counts.items()],
        columns=[column_name, "complaint_count"]
    )
    if not result.empty:
        result = result.sort_values("complaint_count", ascending=False)
        result["percent_of_complaints"] = (
            result["complaint_count"] / len(label_sets) * 100
        ).round(2)
    return result


def explode_complaint_labels(data, label_set_col, output_name):
    """Create one row per complaint-label combination."""
    rows = []
    for _, row in data.iterrows():
        for label in row[label_set_col]:
            rows.append({
                ID_COL: row[ID_COL],
                output_name: label,
                SEVERITY_COL: row[SEVERITY_COL],
                SOURCE_COL: row[SOURCE_COL],
            })
    return pd.DataFrame(rows, columns=[
        ID_COL, output_name, SEVERITY_COL, SOURCE_COL
    ])


# Data loading

def main():
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    if not DATA_FILE.exists():
        print(f"\nCould not find the CSV file:\n{DATA_FILE}")
        print("\nPut the CSV in a folder named 'data' beside this Python file.")
        sys.exit(1)

    df = pd.read_csv(DATA_FILE, low_memory=False)
    required = [ID_COL, BPD_COL, LLM_COL, SEVERITY_COL, SOURCE_COL]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Remove rows without a complaint ID and ensure one record per complaint.
    df = df.dropna(subset=[ID_COL]).copy()
    df[ID_COL] = df[ID_COL].astype(str).str.strip()

    duplicate_count = int(df[ID_COL].duplicated().sum())
    if duplicate_count:
        raise ValueError(
            f"Found {duplicate_count} duplicate complaint IDs. "
            "Review duplicates before running a complaint-level comparison."
        )

    df[BPD_COL] = df[BPD_COL].fillna("")
    df[LLM_COL] = df[LLM_COL].fillna("")
    df[SEVERITY_COL] = df[SEVERITY_COL].fillna("MISSING").astype(str).str.strip()
    df[SOURCE_COL] = df[SOURCE_COL].fillna("MISSING").astype(str).str.strip()

    df["bpd_labels"] = df[BPD_COL].apply(split_labels)
    df["llm_labels"] = df[LLM_COL].apply(split_labels)

    # Keep unmapped status separate from the comparable BPD label set.
    df["has_unmapped_bpd"] = df[BPD_COL].astype(str).str.contains(
        r"(^|\|)\s*UNMAPPED\s*(\||$)", case=False, regex=True
    )
    # Exact per-complaint set comparison.
    # Only calculate additions/omissions when both systems supplied at least
    # one usable label. Blank or wholly unmapped BPD records are analyzed
    # separately below rather than counted as automatically "additional".
    df["has_both_label_sets"] = (
        df["bpd_labels"].map(len).gt(0) & df["llm_labels"].map(len).gt(0)
    )
    df["additional_llm_labels"] = df.apply(
        lambda row: row["llm_labels"] - row["bpd_labels"]
        if row["has_both_label_sets"] else set(), axis=1
    )
    df["not_retained_bpd_labels"] = df.apply(
        lambda row: row["bpd_labels"] - row["llm_labels"]
        if row["has_both_label_sets"] else set(), axis=1
    )
    df["shared_labels"] = df.apply(
        lambda row: row["bpd_labels"] & row["llm_labels"]
        if row["has_both_label_sets"] else set(), axis=1
    )

    n_complaints = len(df)
    comparable = df[
        (df["bpd_labels"].map(len) > 0) &
        (df["llm_labels"].map(len) > 0)
    ].copy()

    print("\nDATASET OVERVIEW")
    print("----------------")
    print(f"Complaints analyzed: {n_complaints:,}")
    print(f"Unique complaint IDs: {df[ID_COL].nunique():,}")
    print(f"Complaints with at least one BPD label: "
          f"{(df['bpd_labels'].map(len) > 0).sum():,}")
    print(f"Complaints with at least one LLM label: "
          f"{(df['llm_labels'].map(len) > 0).sum():,}")
    print(f"Complaints with an unmapped BPD label: "
          f"{df['has_unmapped_bpd'].sum():,}")
    print(f"Complaints with both label sets available: {len(comparable):,}")
    print("Additions and omissions are calculated only for these comparable complaints.")

    # ANALYSIS 1: OVERALL ALLEGATION COMPARISON
    bpd_counts = label_counts(df["bpd_labels"], "bpd_allegation")
    llm_counts = label_counts(df["llm_labels"], "llm_allegation")
    save_table(bpd_counts, "01_bpd_allegation_counts.csv")
    save_table(llm_counts, "01_llm_allegation_counts.csv")

    comparison = pd.merge(
        bpd_counts, llm_counts,
        left_on="bpd_allegation", right_on="llm_allegation",
        how="outer"
    )
    comparison["allegation"] = (
        comparison["bpd_allegation"].combine_first(comparison["llm_allegation"])
    )
    comparison = comparison[[
        "allegation", "complaint_count_x", "percent_of_complaints_x",
        "complaint_count_y", "percent_of_complaints_y"
    ]].rename(columns={
        "complaint_count_x": "bpd_complaint_count",
        "percent_of_complaints_x": "bpd_percent",
        "complaint_count_y": "llm_complaint_count",
        "percent_of_complaints_y": "llm_percent",
    }).fillna(0)
    comparison["count_difference_llm_minus_bpd"] = (
        comparison["llm_complaint_count"] - comparison["bpd_complaint_count"]
    )
    comparison = comparison.sort_values(
        "count_difference_llm_minus_bpd", key=lambda x: x.abs(), ascending=False
    )
    save_table(comparison, "01_overall_bpd_vs_llm_comparison.csv")

    top_compare = comparison.copy()
    top_compare["largest_absolute_difference"] = (
        top_compare["count_difference_llm_minus_bpd"].abs()
    )
    top_compare = top_compare.sort_values(
        "largest_absolute_difference", ascending=False
    ).head(20)
    if not top_compare.empty:
        labels = top_compare["allegation"].astype(str).to_numpy()[::-1]
        bpd_values = top_compare["bpd_complaint_count"].to_numpy()[::-1]
        llm_values = top_compare["llm_complaint_count"].to_numpy()[::-1]
        y = range(len(labels))
        height = 0.38
        plt.figure(figsize=(12, 7))
        plt.barh([i - height / 2 for i in y], bpd_values,
                 height=height, label="BPD")
        plt.barh([i + height / 2 for i in y], llm_values,
                 height=height, label="LLM")
        plt.yticks(list(y), labels)
        plt.xlabel("Number of complaints containing allegation")
        plt.title("BPD vs. LLM Allegation Counts (Top 20 Differences)")
        plt.legend()
        plt.tight_layout()
        plt.savefig(FIGURE_DIR / "01_overall_bpd_vs_llm.png",
                    dpi=200, bbox_inches="tight")
        plt.close()

    # ---------------- ANALYSIS 2: ADDITIONAL LLM ALLEGATIONS ------------
    additional = explode_complaint_labels(
        df, "additional_llm_labels", "additional_llm_allegation"
    )
    additional_counts = (
        additional.groupby("additional_llm_allegation")[ID_COL]
        .nunique().reset_index(name="complaint_count")
        .sort_values("complaint_count", ascending=False)
    )
    if not additional_counts.empty:
        additional_counts["percent_of_all_complaints"] = (
            additional_counts["complaint_count"] / n_complaints * 100
        ).round(2)
    save_table(additional_counts, "02_additional_llm_allegations.csv")

    complaints_with_additions = int(df["additional_llm_labels"].map(len).gt(0).sum())
    additions_summary = pd.DataFrame([{
        "total_complaints": n_complaints,
        "complaints_with_additional_llm_labels": complaints_with_additions,
        "percent_with_additional_llm_labels": round(
            complaints_with_additions / n_complaints * 100, 2
        ) if n_complaints else 0,
    }])
    save_table(additions_summary, "02_additional_llm_summary.csv")
    save_bar_chart(
        additional_counts, "additional_llm_allegation", "complaint_count",
        "Most Frequent Additional LLM Allegations",
        "02_additional_llm_allegations.png"
    )

    # ---------------- ANALYSIS 3: BPD LABELS NOT RETAINED ---------------
    not_retained = explode_complaint_labels(
        df, "not_retained_bpd_labels", "not_retained_bpd_allegation"
    )
    not_retained_counts = (
        not_retained.groupby("not_retained_bpd_allegation")[ID_COL]
        .nunique().reset_index(name="complaint_count")
        .sort_values("complaint_count", ascending=False)
    )
    if not_retained_counts.empty:
        not_retained_counts["percent_of_all_complaints"] = (
            not_retained_counts["complaint_count"] / n_complaints * 100
        ).round(2)
    save_table(not_retained_counts, "03_bpd_allegations_not_retained.csv")
    save_bar_chart(
        not_retained_counts, "not_retained_bpd_allegation", "complaint_count",
        "Most Frequent BPD Allegations Not Retained by LLM",
        "03_bpd_not_retained.png"
    )

    # ---------------- ANALYSIS 4: RECLASSIFICATION PATTERNS -------------
    pairs = []
    for _, row in comparable.iterrows():
        for bpd_label in row["bpd_labels"]:
            for llm_label in row["llm_labels"]:
                pairs.append({
                    "bpd_allegation": bpd_label,
                    "llm_allegation": llm_label,
                    ID_COL: row[ID_COL],
                })

    if pairs:
        pair_df = pd.DataFrame(pairs)
        reclassification = (
            pair_df.groupby(["bpd_allegation", "llm_allegation"])[ID_COL]
            .nunique().reset_index(name="complaint_count")
            .sort_values("complaint_count", ascending=False)
        )
    else:
        reclassification = pd.DataFrame(
            columns=["bpd_allegation", "llm_allegation", "complaint_count"]
        )
    save_table(reclassification, "04_reclassification_pairs.csv")

    if not reclassification.empty:
        top_bpd = reclassification.groupby("bpd_allegation")[
            "complaint_count"
        ].sum().nlargest(15).index
        top_llm = reclassification.groupby("llm_allegation")[
            "complaint_count"
        ].sum().nlargest(15).index
        heat = reclassification[
            reclassification["bpd_allegation"].isin(top_bpd) &
            reclassification["llm_allegation"].isin(top_llm)
        ].pivot_table(
            index="bpd_allegation", columns="llm_allegation",
            values="complaint_count", fill_value=0, aggfunc="sum"
        )
        plt.figure(figsize=(14, 10))
        plt.imshow(heat.values, aspect="auto")
        plt.colorbar(label="Complaint count")
        plt.xticks(range(len(heat.columns)), heat.columns,
                   rotation=60, ha="right")
        plt.yticks(range(len(heat.index)), heat.index)
        plt.xlabel("LLM allegation")
        plt.ylabel("Original BPD allegation")
        plt.title("BPD to LLM Reclassification Patterns (Top Categories)")
        plt.tight_layout()
        plt.savefig(FIGURE_DIR / "04_reclassification_heatmap.png",
                    dpi=200, bbox_inches="tight")
        plt.close()

    # ---------------- ANALYSIS 5: ADDITIONS BY SEVERITY -----------------
    severity_rows = []
    for _, row in df.iterrows():
        for label in row["additional_llm_labels"]:
            severity_rows.append({
                "severity": row[SEVERITY_COL],
                "additional_llm_allegation": label,
                ID_COL: row[ID_COL],
            })
    severity_additions = pd.DataFrame(severity_rows)
    if not severity_additions.empty:
        severity_summary = (
            severity_additions.groupby(
                ["severity", "additional_llm_allegation"]
            )[ID_COL].nunique().reset_index(name="complaint_count")
        )
        severity_summary["percent_within_severity"] = severity_summary.apply(
            lambda r: round(
                r["complaint_count"] /
                max(1, df.loc[df[SEVERITY_COL] == r["severity"], ID_COL].nunique())
                * 100, 2
            ), axis=1
        )
        severity_summary = severity_summary.sort_values(
            ["severity", "complaint_count"], ascending=[True, False]
        )
    else:
        severity_summary = pd.DataFrame(
            columns=["severity", "additional_llm_allegation",
                     "complaint_count", "percent_within_severity"]
        )
    save_table(severity_summary, "05_additional_allegations_by_severity.csv")

    if not severity_summary.empty:
        pivot = severity_summary.pivot_table(
            index="additional_llm_allegation", columns="severity",
            values="complaint_count", fill_value=0, aggfunc="sum"
        )
        top_labels = severity_summary.groupby("additional_llm_allegation")[
            "complaint_count"
        ].sum().nlargest(15).index
        pivot = pivot.loc[pivot.index.intersection(top_labels)]
        plt.figure(figsize=(12, 8))
        plt.imshow(pivot.values, aspect="auto")
        plt.colorbar(label="Complaint count")
        plt.xticks(range(len(pivot.columns)), pivot.columns)
        plt.yticks(range(len(pivot.index)), pivot.index)
        plt.xlabel("Severity")
        plt.ylabel("Additional LLM allegation")
        plt.title("Additional LLM Allegations by Severity")
        plt.tight_layout()
        plt.savefig(FIGURE_DIR / "05_additional_by_severity_heatmap.png",
                    dpi=200, bbox_inches="tight")
        plt.close()

    # ---------------- ANALYSIS 6: DIFFERENCES BY COMPLAINT SOURCE --------
    source_summary = (
        df.assign(has_additional=df["additional_llm_labels"].map(len).gt(0))
        .groupby(SOURCE_COL)
        .agg(
            complaint_count=(ID_COL, "nunique"),
            comparable_complaints=("has_both_label_sets", "sum"),
            complaints_with_additions=("has_additional", "sum"),
            average_bpd_labels=("bpd_labels", lambda x: x.map(len).mean()),
            average_llm_labels=("llm_labels", lambda x: x.map(len).mean()),
        ).reset_index()
    )
    source_summary["percent_with_additions"] = (
        source_summary["complaints_with_additions"] /
        source_summary["comparable_complaints"].replace(0, pd.NA) * 100
    ).fillna(0).round(2)
    source_summary["average_bpd_labels"] = source_summary[
        "average_bpd_labels"
    ].round(2)
    source_summary["average_llm_labels"] = source_summary[
        "average_llm_labels"
    ].round(2)
    save_table(source_summary, "06_classification_differences_by_source.csv")

    source_additions = (
        additional.groupby([SOURCE_COL, "additional_llm_allegation"])[ID_COL]
        .nunique().reset_index(name="complaint_count")
        .sort_values([SOURCE_COL, "complaint_count"], ascending=[True, False])
    ) if not additional.empty else pd.DataFrame()
    save_table(source_additions, "06_additional_labels_by_source.csv")

    if not source_summary.empty:
        plt.figure(figsize=(9, 6))
        plt.bar(source_summary[SOURCE_COL],
                source_summary["percent_with_additions"])
        plt.ylabel("Complaints with additional LLM labels (%)")
        plt.title("Additional LLM Labels by Complaint Source")
        plt.xticks(rotation=15, ha="right")
        plt.tight_layout()
        plt.savefig(FIGURE_DIR / "06_additions_by_source.png",
                    dpi=200, bbox_inches="tight")
        plt.close()

    # ---------------- ANALYSIS 7: UNMAPPED BPD ALLEGATIONS ---------------
    unmapped = df[df["has_unmapped_bpd"]].copy()
    unmapped_summary = pd.DataFrame([{
        "complaints_with_unmapped_bpd": len(unmapped),
        "percent_of_all_complaints": round(
            len(unmapped) / n_complaints * 100, 2
        ) if n_complaints else 0,
        "unmapped_complaints_with_llm_labels": int(
            unmapped["llm_labels"].map(len).gt(0).sum()
        ),
        "percent_unmapped_with_llm_labels": round(
            unmapped["llm_labels"].map(len).gt(0).mean() * 100, 2
        ) if len(unmapped) else 0,
    }])
    save_table(unmapped_summary, "07_unmapped_bpd_summary.csv")

    unmapped_llm_counts = label_counts(
        unmapped["llm_labels"], "llm_allegation"
    ) if len(unmapped) else pd.DataFrame(
        columns=["llm_allegation", "complaint_count", "percent_of_complaints"]
    )
    save_table(unmapped_llm_counts, "07_llm_labels_for_unmapped_bpd.csv")
    save_bar_chart(
        unmapped_llm_counts, "llm_allegation", "complaint_count",
        "LLM Allegations for Complaints with Unmapped BPD Labels",
        "07_unmapped_bpd_llm_labels.png"
    )

    unmapped_severity = (
        unmapped.groupby(SEVERITY_COL)[ID_COL].nunique()
        .reset_index(name="complaint_count")
        .sort_values("complaint_count", ascending=False)
    )
    save_table(unmapped_severity, "07_unmapped_bpd_by_severity.csv")

    # ---------------------- EXPORT COMPLAINT-LEVEL DATA -----------------
    export_cols = [
        ID_COL, SOURCE_COL, SEVERITY_COL,
        "bpd_labels", "llm_labels", "shared_labels",
        "additional_llm_labels", "not_retained_bpd_labels",
        "has_unmapped_bpd",
    ]
    complaint_comparison = df[export_cols].copy()
    for col in [
        "bpd_labels", "llm_labels", "shared_labels",
        "additional_llm_labels", "not_retained_bpd_labels",
    ]:
        complaint_comparison[col] = complaint_comparison[col].apply(
            lambda labels: " | ".join(sorted(labels))
        )
    save_table(complaint_comparison, "complaint_level_comparison.csv")

    print("\nDONE!")
    print(f"Tables saved in: {TABLE_DIR}")
    print(f"Figures saved in: {FIGURE_DIR}")
    print("\nReminder: review LABEL_ALIASES and harmonize equivalent categories")
    print("before treating exact-match additions or omissions as substantive.")


if __name__ == "__main__":
    main()
