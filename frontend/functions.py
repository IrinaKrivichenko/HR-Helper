import pandas as pd
import gradio as gr

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
        'Comment'
    ]

    # Add missing columns with None values
    for col in required_columns:
        if col not in df.columns:
            df[col] = None

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
    print(project_desc, threshold_value)
    print(engagement_checkboxes)

    threshold_value = float(threshold_value)

    df["Works hrs/day"] = df["Works hrs/day"].astype(str)
    hours_condition = df["Works hrs/day"].apply(lambda x: any(substring in x for substring in hours_checkboxes))
    engagement_condition = df["LVL of engagement"].isin(engagement_checkboxes)
    filtered_df = df[hours_condition & engagement_condition]

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

