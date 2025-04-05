import gradio as gr
import pandas as pd
import numpy as np

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
        'Rate In', 'Rate In expected', 'Sell Rate', 'Month In (entry point)',  'Month In (expected)',
        'CV (original)', 'CV white label (gdocs)', 'Folder', 'NDA',
        'Comment',  'Embedding'
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
                # print(embedding.size())
                df.at[index, 'Embedding'] = embedding

    df = df.sort_values(by='First Name', ascending=True)
    return df

def get_field_options(df, field_name):
    # Filter the DataFrame for the specified field name
    options = df[df['field'] == field_name]['value'].unique()
    return options.tolist()


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

