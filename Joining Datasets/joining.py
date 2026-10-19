import pandas as pd
import numpy as np

#importing datasets and converting to csv file
#df_description = pd.read_excel('COMPLAINTS CONVERTED - 2016,17,19,20_corrected_file_final-Spark-spring2024.xlsx')
#df_description.to_csv('Complaints_with_description.csv', index=False)

df_no_description = pd.read_csv('officer_misconduct_all.csv')
df_description = pd.read_csv('complaints_with_description.csv')
#print(df_no_description.head())
#print(df_no_description.columns)
df_complaints = df_no_description.merge(df_description, left_on="IA #", right_on="IA No", how="left")

df_complaints.to_csv('complaints_combined.csv', index=False)

df_complaints_final = pd.read_csv('complaints_combined.csv')
print(df_complaints_final.head())