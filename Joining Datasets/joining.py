import pandas as pd

df_2011_2020 = pd.read_csv('Data/iad_extracted_with_youth_labels_scrubbed.csv')

# Excel file -> read_excel (needs openpyxl: pip install openpyxl)
df_2020_2026 = pd.read_csv('Data/2020_2026_exploded.csv')

df_complaints = pd.concat([df_2011_2020, df_2020_2026], ignore_index=True)
df_complaints_deduped = df_complaints.drop_duplicates()

df_complaints_deduped.to_csv('Data/complaints_combined_deduped.csv', index=False)