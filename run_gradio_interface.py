import pandas as pd
from frontend.gradio_interface import create_interface

def load_data(file_path):
    df = pd.read_excel(file_path)
    df.columns = df.columns.str.strip()

    # Определяем список всех необходимых столбцов
    required_columns = [
        'First Name', 'Last Name', 'LVL of engagement', 'Works hrs/day',
        'From', # From not in the UI
        'LinkedIn', 'Telegram', 'Phone', 'Email',
        'Seniority', 'Role', 'Stack', 'Industry', 'Expertise',
        'Belarusian', 'English', 'Location',
        'Rate In', 'Rate In expected', 'Sell Rate', 'Month In (entry point)',
        'CV (original)', 'CV white label (gdocs)', 'Folder', 'NDA',
        'Comment'
    ]
    for col in required_columns:
        if col not in df.columns:
            df[col] = None

    return df

if __name__ == "__main__":
    df = load_data('data/Staff.xlsx')
    interface = create_interface(df)
    interface.launch()
