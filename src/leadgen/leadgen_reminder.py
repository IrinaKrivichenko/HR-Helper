from datetime import datetime

from src.google_services.sheets import read_specific_columns

class LeadGenReminder:

    def __init__(self):
        self.users_to_send = {"Andrus":  694614399}
        self.application = None


    def set_application(self, application):
        self.application = application

    async def remind_to_send_message(self):
        pass
        columns = ["First Name", "Last Name", "LinkedIn Profile", "Industry", "Статус ліда (Andrus)", "M0 Andrus", "Статус ліда (Juras)"]
        leads_df = read_specific_columns(columns_to_extract=columns, sheet_name="Leads CRM", spreadsheet_env_name='ΛV_LINKEDIN_LEADGEN_SPREADSHEET_ID')
        print("len(leads_df)", len(leads_df))
        filtered_leads = leads_df[(leads_df["Статус ліда (Juras)"] != "Не ЦА") & (leads_df["LinkedIn Profile"] != '') ]
        print("len(filtered_leads)", len(filtered_leads))
        print(filtered_leads["LinkedIn Profile"])
        today = datetime.now().strftime("%d-%m-%Y")
        for user in self.users_to_send:
            done_today = leads_df[leads_df[f"M0 {user}"] == today].shape[0]
            num_of_rows_to_do = 10 - done_today
            user_filtered_leads = filtered_leads[(filtered_leads[f"Статус ліда ({user})"] == "")].head(num_of_rows_to_do)

            for _, row in user_filtered_leads.iterrows():
                message = (f"Please send an M0 message to  <a href= {row['LinkedIn Profile']}>{row['Last Name']}</a>")
                print(message)
                await self.application.bot.send_message(chat_id=self.users_to_send[user], text=message) #, parse_mode='HTML')

leadgen_reminder = LeadGenReminder()

