from src.google_services.sheets import read_specific_columns


# async \
def remind_to_send_message():
    pass
    columns = ["First Name", "Last Name", "LinkedIn Profile", "Industry", "Статус ліда t.me/AndrusKr", "M0 Andrus", "Статус ліда (Juras)"]
    leads_df = read_specific_columns(columns_to_extract=columns, sheet_name="Leads CRM", spreadsheet_env_name='ΛV_LINKEDIN_LEADGEN_SPREADSHEET_ID')
    print("leads_df.keys() :", leads_df.keys())


