import re

import gradio as gr
import pandas as pd
import io
import tempfile
import openpyxl
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)


from nltk.tokenize import word_tokenize
from nltk.data import path as nltk_path
nltk_path.append('nltk_data')

from src.data_processing.nlp.tokenization import LocalModelHandler as LLMHandler

NUMBER_OF_SPECIALIST_FIELDS = 26
ATTENTION_SIGN = "⚠️"


def load_fields(file_path='frontend/fields_values.xlsx'):
    fields = pd.read_excel(file_path)
    return fields

def validate_stack_field(stack_content, llm_handler):
    prompt = [
        {"role": "system", "content": "You are an expert in analyzing technical stacks."},
        {"role": "user", "content": (
            f"Please verify if the following 'Stack' field contains specific technologies and libraries required for projects. "
            f"A valid stack should include specific technologies and libraries that are relevant to the project requirements. "
            f"Here are some examples of valid stacks:\n"
            f"1. 'Java 21, Kafka, MySQL, Google Guice, DropWizard, Maven, JUnit, Mockito, React, Git, Intellij IDEA, Orion, OpenGrok, LogFetch, JIRA, Sentry & Singularity'\n"
            f"2. 'Linux, Python, R, C++, C, SQL, Jupyter, Git, Docker, Amazon Web Services (AWS), Matlab, NumPy, Pandas, MatPlotLib, Plotly, Seaborn, Scikit-learn, TensorFlow, Keras, OpenCV, XGBoost, Catboost, SciPy, ARIMA'\n"
            f"3. 'Swift SnapKit UserDefaults CocoaPods, SwiftPM MVVM, MVVM+C, MVC Realm, SwiftData Stinsen UIKit SwiftUI StoreKit Autolayout URLSession GCD ARC Tools Swift SnapKit UserDefaults CocoaPods, SwiftPM MVVM, MVVM+C, MVC Realm, SwiftData Stinsen UIKit SwiftUI StoreKit Autolayout URLSession GCD ARC Xcode Jira Notion MongoDB Git Figma Postico Postman'\n"
            f"4. 'Python, C++, PyTorch, Lightning, Catalyst, Ultralytics, NumPy, Seaborn, Sklearn, Matplotlib, Pandas, LightGBM, XGBoost, CatBoost, Detectron2, OpenCV, W&B, TensorRT, CVAT'\n"
            f"5. 'Python, Django, Docker, FastApi, Kubernetes'\n"
            f"6. 'LLM, Computer Vision, NLP, Recommendation Systems, Time Series, Speech'\n"
            f"7. 'Computer Vision, \nGCP, \nDevOps, \nAWS'\n"
            f"8. 'Jira, Confluence, Azure DevOps, Trello, Slack, MS Teams, Figma, Miro'\n"
            f"9. 'JavaScript\nReact\nRedux\nHTML\nCSS\nSASS'\n\n"
            f"10. 'Python, R,  MLflow,  Angular, Spring, FastAPI'\n"
            f"An example of an invalid stack:\n"
            f"'Python, C#, Delphi, C++, Visual'\n\n"
            f"Now, evaluate the following stack content: '{stack_content}'. "
            
            f"Respond with 'Yes' if it is a valid stack, or 'No' if it is not."
        )}
    ]
    response = llm_handler.get_answer(prompt , max_tokens=1)
    if "yes" in response.lower():
        return True
    else:
        return False

def get_relevant_roles(stack_content, role_content, role_options, llm_handler):
    prompt = [
        {"role": "system", "content": "You are an expert in matching technical stacks to job roles."},
        {"role": "user", "content": (
            f"Given the following 'Stack' content: '{stack_content}' and the current 'Role': '{role_content}', "
            f"determine the most relevant roles from the following list: {', '.join(role_options)}. "
            f"Return the relevant roles in order of relevance, separated by commas."
        )}
    ]
    response = llm_handler.get_answer(prompt)
    return response

def _get_cell_content(cell):
    text = cell.value
    link = cell.hyperlink.target if cell.hyperlink else None
    return link if link else text

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
    df = df.reset_index(drop=True)
    return df

def load_data(file_path):
    """
    Load data from an Excel or CSV file into a DataFrame.

    Parameters:
    - file_path (str): The path to the Excel or CSV file.

    Returns:
    - pd.DataFrame: The loaded DataFrame.
    """

    # Determine the file type based on the file extension
    if file_path.endswith('.xlsx') or file_path.endswith('.xls'):
        # Read the Excel file into a DataFrame
        df = pd.read_excel(file_path)

        # Load the workbook and select the active sheet
        wb = openpyxl.load_workbook(file_path)
        ws = wb.active

        # Iterate over each cell in the DataFrame and replace the values
        for row_idx, row in df.iterrows():
            for col_idx, col in enumerate(df.columns, start=1):
                cell = ws.cell(row=row_idx + 2, column=col_idx)  # +2 to account for the header
                df.at[row_idx, col] = _get_cell_content(cell)
    elif file_path.endswith('.csv'):
        # Read the CSV file into a DataFrame
        df = pd.read_csv(file_path, sep=';')
    else:
        raise ValueError("Unsupported file format. Please provide an Excel or CSV file.")

    df = adjust_dataframe_structure(df)
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
    sorted_df = sorted_df.reset_index(drop=True)
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
    # if matching_tokens_count > 1:
    #     print(row_tokens & project_tokens)
    return matching_tokens_count

def filter_and_update_specialists(
                df,
                project_desc, threshold_value,
                hours_checkboxes, engagement_checkboxes):
    # df["Works hrs/day"] = df["Works hrs/day"].astype(str)
    # hours_condition = df["Works hrs/day"].apply(lambda x: any(substring in x for substring in hours_checkboxes))
    engagement_condition = df["LVL of engagement"].isin(engagement_checkboxes)
    # filtered_df = df[hours_condition & engagement_condition]
    filtered_df = df[engagement_condition]
    filtered_df = filtered_df.reset_index(drop=True)

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
        # print(filtered_df[["First Name" , "Last Name"  ,  "Matching_Tokens_Count"]])
        threshold_value = int(threshold_value)
        filtered_df = filtered_df.loc[filtered_df['Matching_Tokens_Count'] >= threshold_value]

    # Update filter status and specialist count labels
    is_full_list = len(filtered_df) == len(df)
    filter_status = "Showing full specialist base" if is_full_list else "Showing filtered specialists based on project description"
    specialist_count = f"Total number of specialists: {len(filtered_df)}"
    gr_btn_update = gr.update(visible=is_full_list)
    gr_field_update = gr.update(interactive=is_full_list)

    return (filtered_df[["First Name", "Last Name"]], filtered_df , filter_status, specialist_count,
            *([gr_btn_update] * 4),  # Visibility for buttons to edit with list of specialists
            *([gr_field_update] * NUMBER_OF_SPECIALIST_FIELDS))  # Interactive state for specialist's fields



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
        row["Comment"], selected_index
    )


# function for updating DataFrame
def update_specialist_field(new_value, current_row, field_name, df):
    if current_row >= len(df):
        new_df = df.append(pd.Series("" * len(df.columns), index=df.columns), ignore_index=True)
    else:
        new_df = df.copy()
    new_df.iloc[current_row, df.columns.get_loc(field_name)] = new_value
    return (new_df, new_df[["First Name", "Last Name"]])

def validate_specialist_data(df, llm_handler):
    candidates_valid = []
    candidates_to_review = []
    for index, row in df.iterrows():
        stack = row["Stack"]
        # Example validation: if any of the fields are empty, add to the list
        if stack and validate_stack_field(stack, llm_handler):
            candidates_valid.append(index)
        else:
            candidates_to_review.append(index)
    return candidates_valid, candidates_to_review

def update_relevant_rows(df, indices, llm_handler):
    # Load possible roles
    fields_values_df = load_fields()
    role_options = get_field_options(fields_values_df, "Role")
    for index in indices:
        stack_content = df.at[index, "Stack"]
        role_content = df.at[index, "Role"]
        # Get relevant roles from LLM
        relevant_roles = get_relevant_roles(stack_content, role_content, role_options, llm_handler)
        # Update a row in a DataFrame
        df.at[index, "Role"] = relevant_roles
    return df

def switch_to_validation_mode(df):
    mode = "validate"
    llm_handler = LLMHandler()
    candidates_valid, candidates_to_review = validate_specialist_data(df, llm_handler)
    df_to_review = df.iloc[candidates_to_review]
    print(df_to_review[["First Name", "Last Name", "Stack"]])
    full_df = update_relevant_rows(df, candidates_valid, llm_handler)
    gr_btn_update = gr.update(visible=False)
    filter_status = f"Switched to validation mode. \n\n{ATTENTION_SIGN} Don't forget to save after editing."
    specialist_count = f"{ATTENTION_SIGN} Please review the candidates as their 'Stack' field must specify the technologies and libraries required for projects."
    # specialist_count = "Please review the candidates as their 'Stack' field is incomplete or missing."
    return (mode, df_to_review,  df_to_review[["First Name", "Last Name"]], full_df,
            *([gr_btn_update] * 3), filter_status, specialist_count)



def delete_specialist(current_row, df):
    if 0 <= current_row < len(df):
        new_df = df.drop(index=current_row).reset_index(drop=True)
    else:
        new_df = df
    # current_row = len(new_df)
    # empty_values = [""] * NUMBER_OF_SPECIALIST_FIELDS
    return (new_df, new_df[["First Name", "Last Name"]],
            *clear_specialists_fields(df))

def clear_specialists_fields(df):
    new_row_index = len(df)
    filter_status = "Showing full specialist base"
    specialist_count = f"Total number of specialists: {new_row_index}"
    gr_btn_update = gr.update(visible=True)
    gr_field_update = gr.update(interactive=True)
    return (new_row_index, filter_status, specialist_count,
            *([gr_btn_update] * 4),  # Visibility for buttons to edit with list of specialists
            *([gr_field_update] * NUMBER_OF_SPECIALIST_FIELDS))  # Interactive state for specialist's fields

def save_specialist_data(mode, df, full_df, path):
    """
    Save the specialist data based on the current mode.
    Parameters:
    - mode (str): The current mode of the application ('standard' or 'validate').
    - df (pd.DataFrame): The current DataFrame containing specialist data.
    - full_df (pd.DataFrame or None): The full DataFrame containing all specialist data when in 'validate' mode.
    Returns:
    - bool: Returns True to trigger a UI refresh.
    """
    if mode == "validate" and full_df is not None:
        # Update rows in df that match "First Name" and "Last Name" from full_df
        for index, row in df.iterrows():
            matching_indices = full_df[
                (full_df["First Name"] == row["First Name"]) &
                (full_df["Last Name"] == row["Last Name"])
                ].index
            if not matching_indices.empty:
                for col in full_df.columns:
                    full_df.at[matching_indices[0], col] = row[col]
        df = full_df
        full_df = None

    # Save the updated DataFrame to an Excel file
    df.to_excel(path, index=False)

    return ("standard", df, full_df,
            df[["First Name", "Last Name"]],
            *clear_specialists_fields(df))


