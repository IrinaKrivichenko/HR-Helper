import re

import gradio as gr
import pandas as pd
import numpy as np
import io
import tempfile
from pathlib import Path
import logging
logging.basicConfig(level=logging.INFO)

from nltk.util import ngrams
from nltk.tokenize import word_tokenize
from nltk.data import path as nltk_path
nltk_path.append('nltk_data')

from api_handlers.EmbeddingHandler import EmbeddingHandler

embedding_handler = EmbeddingHandler()

def adjust_dataframe_structure(df):
    # Strip any leading or trailing whitespace from column names
    df.columns = df.columns.str.strip()
    # Define the list of all required columns
    required_columns = [
        'First Name', 'Last Name', 'LVL of engagement', 'Works hrs/day',
        'LinkedIn', 'Telegram', 'Phone', 'Email',
        'Seniority', 'Role', 'Stack', 'Industry', 'Expertise',
        'Belarusian', 'English', 'Location',
        'Rate In', 'Rate In expected', 'Sell Rate', 'Month In (entry point)', 'Month In (expected)',
        'CV (original)', 'CV white label (gdocs)', 'Folder', 'NDA',
        'Comment', 'Embedding'
    ]
    # Add missing columns with None values
    for col in required_columns:
        if col not in df.columns:
            df[col] = ''

    df = df.fillna('')

    # # Calculate embeddings for rows where 'Embedding' is None
    # for index, row in df.iterrows():
    #     if row['Embedding'] is None:
    #         # Concatenate text fields to create a single string for embedding
    #         text_fields = [row['Role'], row['Stack'], row['Industry'], row['Expertise']]
    #         text_for_embedding = " ".join(str(field) for field in text_fields if pd.notna(field))
    #         if text_for_embedding:
    #             embedding = embedding_handler.get_text_embedding(text_for_embedding)
    #             df.at[index, 'Embedding'] = embedding
    #
    # # Convert string representations of embeddings back to arrays if necessary
    # def string_to_array(s):
    #     if isinstance(s, str) and s.strip():
    #         # Remove brackets and split the string into elements
    #         s = s.replace("[", "").replace("]", "")
    #         elements = np.fromstring(s, sep=',')
    #         return elements.reshape(1, -1)  # Assuming it's a 2D array with one row
    #     return s
    #
    # df['Embedding'] = df['Embedding'].apply(string_to_array)

    # Sort the DataFrame by 'First Name'
    df = df.sort_values(by='First Name', ascending=True)

    return df


def get_field_options(df, field_name):
    # Check if the column exists in the DataFrame
    if field_name in df.columns:
        # Return a list of unique values from the column
        return df[field_name].unique().tolist()
    else:
        # Filter the DataFrame for the specified field name
        options = df[df['field'] == field_name]['value'].unique()
        return options.tolist()


def download_bench_df(df):
    old_new_columns_dict = {
        'First Name': "Name",
        'Works hrs/day': "Works hrs/day",
        'Seniority': "Seniority",
        'Role': "Roles",
        'Stack': "Stack",
        'Industry': "Industry",
        'Expertise': "Expertise",
        'English': "English",
        'Location': "Location",
        'Sell Rate': "Rate",
        'CV white label (gdocs)': "CV white label (gdocs)"
    }
    # Filter the DataFrame, leaving only the columns that are in the dict
    bench_df = df[old_new_columns_dict.keys()]
    bench_df = bench_df.rename(columns=old_new_columns_dict)
    return download_staff_df(bench_df, filename='bench_data.xlsx')


def download_staff_df(df, filename='staff_data.xlsx'):
    try:
        # Создаем объект BytesIO для записи данных в памяти
        output = io.BytesIO()

        # Используем ExcelWriter для записи DataFrame в формат Excel
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Staff')

        # Перемещаем курсор в начало объекта BytesIO
        output.seek(0)

        # Создаем временный файл с указанным именем
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx", dir=tempfile.gettempdir()) as tmp_file:
            tmp_file.write(output.getvalue())
            temp_file_path = tmp_file.name

        # Переименовываем файл, чтобы он назывался в соответствии с параметром filename
        final_path = Path(tempfile.gettempdir()) / filename
        Path(temp_file_path).rename(final_path)
        temp_file_path = final_path

        logging.info(f"File successfully created at: {str(temp_file_path)}")
        return str(temp_file_path)
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        raise


def sort_dataframe(df, sort_column, ascending=True):
    sorted_df = df.sort_values(by=sort_column, ascending=ascending)
    return sorted_df[["First Name", "Last Name"]], sorted_df

def get_tokens(text):
    tokens = word_tokenize(text.lower())
    english_letter_pattern = re.compile(r'[a-zA-Z]')
    filtered_tokens = [token for token in tokens if english_letter_pattern.search(token)]
    return set(filtered_tokens)

# Function to count identical tokens
def count_matching_tokens(row, project_tokens):
    text_fields = [row['Role'], row['Stack'], row['Industry'], row['Expertise']]
    combined_text = " ".join(str(field) for field in text_fields if pd.notna(field))
    combined_text = combined_text if combined_text else ""
    row_tokens = get_tokens(combined_text)
    matching_tokens_count = len(row_tokens & project_tokens)
    print(type(matching_tokens_count), matching_tokens_count)
    return matching_tokens_count

def filter_and_update_specialists(
                df,
                project_desc, threshold_value,
                hours_checkboxes, engagement_checkboxes):
    df["Works hrs/day"] = df["Works hrs/day"].astype(str)
    hours_condition = df["Works hrs/day"].apply(lambda x: any(substring in x for substring in hours_checkboxes))
    engagement_condition = df["LVL of engagement"].isin(engagement_checkboxes)
    filtered_df = df[hours_condition & engagement_condition]

    if project_desc:
        if project_desc:
            project_desc_tokens = get_tokens(project_desc)

        # Apply the function and add a new column
        filtered_df = filtered_df.copy()  # Create a copy to avoid SettingWithCopyWarning
        filtered_df['Matching_Tokens_Count'] = filtered_df.apply(
            lambda row: count_matching_tokens(row, project_desc_tokens),
            axis=1
        )
        # Convert the column to a numeric data type
        filtered_df['Matching_Tokens_Count'] = pd.to_numeric(filtered_df['Matching_Tokens_Count'], errors='coerce')
        # Filter the DataFrame
        pd.set_option('display.max_rows', None)
        print(filtered_df[["First Name" , "Last Name"  ,  "Matching_Tokens_Count"]])
        threshold_value = int(threshold_value)
        filtered_df = filtered_df.loc[filtered_df['Matching_Tokens_Count'] >= threshold_value]

    # Update filter status and specialist count labels
    filter_status = "Showing full specialist base" if len(filtered_df) == len(df) else "Showing filtered specialists based on project description"
    specialist_count = f"Total number of specialists: {len(filtered_df)}"

    return filtered_df[["First Name", "Last Name"]] , filtered_df , filter_status, specialist_count


def update_specialist_info(evt: gr.SelectData, df):
    # Get the index of the selected row from evt.index
    selected_index = evt.index[0] if evt.index else 0
    row = df.iloc[selected_index]
    return (
        row["First Name"], row["Last Name"], row["LVL of engagement"], row["Works hrs/day"],
        row["LinkedIn"],  row["Telegram"], row["Phone"], row["Email"],
        row["Seniority"], row["Role"], row["Stack"], row["Industry"], row["Expertise"],
        row["Belarusian"], row["English"], row["Location"],
        row["Rate In"], row["Rate In expected"], row["Sell Rate"], row["Month In (entry point)"], row["Month In (expected)"],
        row["CV (original)"], row["CV white label (gdocs)"], row["Folder"], row["NDA"],
        row["Comment"]
    )

def save_dataframe_to_csv(df, file_path):
    """
    Save the DataFrame to a CSV file, ensuring embeddings are properly converted to strings.

    Parameters:
    - df (pd.DataFrame): The DataFrame to save.
    - file_path (str): The path where the CSV file will be saved.
    """

    # Convert embeddings to strings for saving to CSV
    # This ensures that the embeddings are stored in a format that can be easily read back
    df['Embedding'] = df['Embedding'].apply(lambda x: np.array2string(x, separator=' ', max_line_width=np.inf) if isinstance(x, np.ndarray) else x)

    # Save the DataFrame to a CSV file
    # Using a semicolon as the separator to handle potential commas in the embedding strings
    df.to_csv(file_path, index=False, sep=';')

    print(f"DataFrame successfully saved to {file_path}")

# save_dataframe_to_csv(df, 'data/Staff_with_embeddings.csv')

