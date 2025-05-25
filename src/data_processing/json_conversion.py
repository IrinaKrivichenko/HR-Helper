import json


def df_to_json(df):
    """
    Converts a DataFrame to a JSON string, excluding columns with missing values.

    Args:
    - df (pd.DataFrame): DataFrame containing data.

    Returns:
    - str: JSON string representation of the DataFrame.
    """
    # Convert DataFrame to a list of dictionaries
    records = df.to_dict(orient='records')

    # Filter out keys with None values
    filtered_records = []
    for record in records:
        filtered_record = {k: v for k, v in record.items() if v is not None}
        filtered_records.append(filtered_record)

    # Convert the list of dictionaries to a JSON string
    json_string = json.dumps(filtered_records, ensure_ascii=False, indent=4)

    return json_string