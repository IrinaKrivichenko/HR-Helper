import pandas as pd
from frontend.gradio_interface import create_interface

def load_data(file_path):
    df = pd.read_excel(file_path)
    return df

if __name__ == "__main__":
    df = load_data('data/Staff.xlsx')
    fields_values_df = load_data('frontend/fields_values.xlsx')
    engagement_value = fields_values_df.loc[fields_values_df['field'] == 'LVL of engagement', 'value'].iloc[0]
    interface = create_interface(df, fields_values_df)
    interface.launch()
