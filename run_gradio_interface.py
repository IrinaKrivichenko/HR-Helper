import numpy as np

from frontend.functions import adjust_dataframe_structure
from frontend.gradio_interface import create_interface
import pandas as pd
import openpyxl

def _get_cell_content(cell):
    text = cell.value
    link = cell.hyperlink.target if cell.hyperlink else None
    return link if link else text

def load_fields(file_path):
    fields = pd.read_excel(file_path)
    return fields


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

        # Convert string representations of embeddings back to arrays if necessary
        def string_to_array(s):
            if isinstance(s, str) and s.strip():
                # Remove brackets and split the string into elements
                s = s.replace("[", "").replace("]", "")
                elements = np.fromstring(s, sep=' ')
                return elements.reshape(1, -1)  # Assuming it's a 2D array with one row
            return s

        df['Embedding'] = df['Embedding'].apply(string_to_array)
        original_value = df['Embedding'].iloc[0]
        print("Original Shape:", np.array(original_value).shape if isinstance(original_value, np.ndarray) else "N/A")

    else:
        raise ValueError("Unsupported file format. Please provide an Excel or CSV file.")

    return df


if __name__ == "__main__":
    # df = load_data('data/Staff.xlsx')
    df = load_data('data/Staff_with_embeddings.csv')
    fields_values_df = load_fields('frontend/fields_values.xlsx')
    # engagement_value = fields_values_df.loc[fields_values_df['field'] == 'LVL of engagement', 'value'].iloc[0]
    interface = create_interface(df, fields_values_df)
    interface.launch()
