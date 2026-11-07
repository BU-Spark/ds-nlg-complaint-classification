import pandas as pd

df_2011_2020 = pd.read_csv('Data/iad_extracted_with_youth_labels_scrubbed.csv')

# Excel file -> read_excel (needs openpyxl: pip install openpyxl)
df_2020_2026 = pd.read_excel('Data/Mikaela McSharry MuckRock B2026-519.xlsx')

# Optional: save a CSV copy for the repo, but keep using the DataFrame
df_2020_2026.to_csv('Data/2020_2026.csv', index=False)

df_complaints = df_2011_2020.merge(
    df_2020_2026,
    left_on="ia_no",
    right_on="Inc: IA No",
    how="outer",
)

df_complaints.to_csv('Data/complaints_combined.csv', index=False)
#print(df_complaints.head())

df_complaints = pd.read_csv('Data/complaints_combined.csv')
df_complaints_deduped = df_complaints.drop_duplicates()

df_complaints_deduped.to_csv('Data/complaints_combined_deduped.csv', index=False)