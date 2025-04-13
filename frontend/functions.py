import gradio as gr
import pandas as pd
import numpy as np
import io
import tempfile
from pathlib import Path
import logging
logging.basicConfig(level=logging.INFO)

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
            df[col] = None

    # Calculate embeddings for rows where 'Embedding' is None
    for index, row in df.iterrows():
        if row['Embedding'] is None:
            # Concatenate text fields to create a single string for embedding
            text_fields = [row['Role'], row['Stack'], row['Industry'], row['Expertise']]
            text_for_embedding = " ".join(str(field) for field in text_fields if pd.notna(field))
            if text_for_embedding:
                embedding = embedding_handler.get_text_embedding(text_for_embedding)
                df.at[index, 'Embedding'] = embedding

    # Convert string representations of embeddings back to arrays if necessary
    def string_to_array(s):
        if isinstance(s, str) and s.strip():
            # Remove brackets and split the string into elements
            s = s.replace("[", "").replace("]", "")
            elements = np.fromstring(s, sep=',')
            return elements.reshape(1, -1)  # Assuming it's a 2D array with one row
        return s

    df['Embedding'] = df['Embedding'].apply(string_to_array)

    # Sort the DataFrame by 'First Name'
    df = df.sort_values(by='First Name', ascending=True)

    return df


def get_field_options(df, field_name):
    # Filter the DataFrame for the specified field name
    options = df[df['field'] == field_name]['value'].unique()
    return options.tolist()


def download_staff_df(df_state):
    try:
        # Создаем объект BytesIO для записи данных в памяти
        output = io.BytesIO()

        # Используем ExcelWriter для записи DataFrame в формат Excel
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_state.to_excel(writer, index=False, sheet_name='Staff')

        # Перемещаем курсор в начало объекта BytesIO
        output.seek(0)

        # Создаем временный файл с именем 'staff_data.xlsx'
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx", prefix="staff_data_",
                                         dir=tempfile.gettempdir()) as tmp_file:
            tmp_file.write(output.getvalue())
            temp_file_path = tmp_file.name

        # Переименовываем файл, чтобы он назывался 'staff_data.xlsx'
        final_path = Path(tempfile.gettempdir()) / "staff_data.xlsx"
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

def filter_and_update_specialists(
                df,
                project_desc, threshold_value,
                hours_checkboxes, engagement_checkboxes):
    df["Works hrs/day"] = df["Works hrs/day"].astype(str)
    hours_condition = df["Works hrs/day"].apply(lambda x: any(substring in x for substring in hours_checkboxes))
    engagement_condition = df["LVL of engagement"].isin(engagement_checkboxes)
    filtered_df = df[hours_condition & engagement_condition]

    if project_desc:
        # Get embedding for the project description
        project_embedding = embedding_handler.get_text_embedding(project_desc)

        # Filter out rows with missing embeddings
        valid_embeddings = filtered_df['Embedding'].apply(lambda x: x is not None and not np.isnan(x).any())
        filtered_df_with_embeddings = filtered_df[valid_embeddings]

        if not filtered_df_with_embeddings.empty:
            # Calculate cosine similarity between project embedding and specialist embeddings
            specialist_embeddings = np.array(filtered_df_with_embeddings['Embedding'].tolist()).squeeze()

            # Use FAISS to compute cosine similarity
            # faiss.normalize_L2(specialist_embeddings)
            # faiss.normalize_L2(project_embedding)
            similarities = np.dot(specialist_embeddings, project_embedding.T)

            # Filter specialists based on the threshold value
            threshold_value = float(threshold_value)
            similarity_condition = similarities >= threshold_value
            final_filtered_indices = filtered_df_with_embeddings.index[similarity_condition.flatten()]
            filtered_df = filtered_df.loc[final_filtered_indices]

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

