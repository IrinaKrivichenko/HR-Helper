import pandas as pd
import gradio as gr

def filter_and_update_specialists(df, project_desc, threshold_value):
    # Пример фильтрации: оставляем только тех, у кого LVL of engagement выше заданного порога
    print(project_desc, threshold_value)

    threshold_value = float(threshold_value)
    filtered_df = df[df["LVL of engagement"] >= threshold_value]
    return filtered_df[["First Name", "Last Name"]]

def update_specialist_info(evt: gr.SelectData, df):
    # Получаем индекс выбранной строки из evt.index
    selected_index = evt.index[0] if evt.index else 0
    specialist = df.iloc[selected_index]
    return (
        specialist["First Name"],
        specialist["Last Name"],
        specialist["LVL of engagement"],
        specialist["Works hrs/day"],
        specialist["LinkedIn"],
        specialist["Telegram"],
        specialist["Phone"],
        specialist["Email"],
        specialist["Seniority"],
        specialist["Role"],
        specialist["Stack"],
        specialist["Industry"],
        specialist["Expertise"],
        specialist["Belarusian"],
        specialist["English"],
        specialist["Location"],
        specialist["CV (original)"],
        specialist["CV white label (gdocs)"],
        specialist["Folder"],
        specialist["Rate In"],
        specialist["Rate In expected"],
        specialist["Sell Rate"],
        specialist["Month In (entry point)"],
        specialist["Month In (expected)"],
        specialist["NDA"],
        specialist["Comment"]
    )
