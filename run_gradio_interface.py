from src.frontend.functions import load_fields
from src.frontend.gradio_interface import create_interface

if __name__ == "__main__":
    path = 'data/Staff.xlsx'
    fields_values_df = load_fields()
    # engagement_value = fields_values_df.loc[fields_values_df['field'] == 'LVL of engagement', 'value'].iloc[0]
    interface = create_interface(path, fields_values_df)
    interface.launch()
