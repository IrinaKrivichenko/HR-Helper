import json
from datetime import datetime
from pathlib import Path
import re
import locale
from datetime import datetime, timedelta

import pandas as pd
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

from src.google_services.sheets import read_specific_columns, write_value_to_cell, get_column_letters
from src.leadgen.thnx_for_connection_msg import generate_thnx_for_connection_msg


def extract_links_from_text(text):
    # Регулярное выражение для поиска ссылок в формате <a href="URL">TEXT</a>
    pattern = r'<a\s+href="([^"]+)">[^<]+<\/a>'
    links = re.findall(pattern, text)
    return links

class LeadGenReminder:



    def __init__(self):
        self.users_to_send = {"Andrus":  381735431}  # 694614399}
        # self.users_to_send = {"Andrus":  694614399}
        self.number_of_leads_for_a_day = 10
        self._update_in_cache_leads_df()
        self.application = None


    def set_application(self, application):
        self.application = application
        self.register_handlers(application)


    def _get_today_file_path(self):
        today = datetime.now().strftime("%Y-%m-%d")
        downloads_dir = Path("downloads")
        downloads_dir.mkdir(exist_ok=True)
        return downloads_dir / f" {today}.json"

    def _read_processed_leads(self):
        file_path = self._get_today_file_path()
        if not file_path.exists():
            initial_data = {
                "processed_counts": {user: 0 for user in self.users_to_send.keys()},
                "skipped_indices": {user: [] for user in self.users_to_send.keys()}
            }
            return initial_data
        with open(file_path, "r") as f:
            data = json.load(f)
        return data

    def _update_processed_lead(self, user):
        file_path = self._get_today_file_path()
        data = self._read_processed_leads()
        data["processed_counts"][user] += 1
        with open(file_path, "w") as f:
            json.dump(data, f)

    def _add_skipped_lead(self, user, index):
        file_path = self._get_today_file_path()
        data = self._read_processed_leads()
        if index not in data["skipped_indices"][user]:
            data["skipped_indices"][user].append(index)
        with open(file_path, "w") as f:
            json.dump(data, f)


    async def get_next_lead(self, user):
        data = self._read_processed_leads()
        done_today = data["processed_counts"].get(user, 0)
        skipped_indices = data["skipped_indices"].get(user, [])
        if done_today >= self.number_of_leads_for_a_day:
                return None, done_today

        contact_leads = self.leads_df[(self.leads_df[f"Статус ліда ({user})"] == "Contact")
                                 & (self.leads_df["LinkedIn Profile"] != '')
                                 & (~self.leads_df.index.isin(skipped_indices))]
        if not contact_leads.empty:
            for index, row in contact_leads.iterrows():
                return row, done_today

        filtered_leads = self.leads_df[(self.leads_df["Статус ліда (Juras)"] != "Не ЦА")
                                  & (self.leads_df["LinkedIn Profile"] != '')
                                  & (~self.leads_df.index.isin(skipped_indices))]
        user_filtered_leads = filtered_leads[(filtered_leads[f"Статус ліда ({user})"] == "")
                                | (self.leads_df[f"Статус ліда ({user})"] == "Contact")]
        if len(user_filtered_leads) == 0:
            return None, done_today
        for index, row in user_filtered_leads.iterrows():
            if row[f"M0 {user}"]=='':
                return row, done_today
        return None, done_today

    async def send_next_message(self, user):
        row, done_today = await self.get_next_lead(user)
        if row is None:
            if done_today >= self.number_of_leads_for_a_day:
                await self.application.bot.send_message(
                    chat_id=self.users_to_send[user],
                    text="The leadgen task for today is complete."
                )
            else:
                await self.application.bot.send_message(
                    chat_id=self.users_to_send[user],
                    text="No more leads to process."
                )
            return
        linkedin_profile = row['LinkedIn Profile']
        first_name = row['First Name'] if row['First Name'] else "name not defined"
        last_name = row['Last Name']
        suggested_outreach = row['Suggested Outreach']
        index = row.name
        todays_number = f"{done_today+1} of {self.number_of_leads_for_a_day}\n"
        links = f'<a href="{linkedin_profile}">{first_name} {last_name}</a> - <a href="https://docs.google.com/spreadsheets/d/1ksKFLOutQZI4MgQxvodqeAuHBri5IYQVPTFXXd1SyXo/edit?gid=404358083#gid=404358083&range={index+2}:{index+2}">LeadGen</a>'
        if row[f"Статус ліда ({user})"] == "Contact":
            keyboard = [
                [
                    InlineKeyboardButton("Thanks message", callback_data=f"thanks_{index}_{user}_{done_today + 1}"),
                    InlineKeyboardButton("Skip", callback_data=f"skip_{index}_{user}_{done_today + 1}")
                ]
            ]
            message = f'{todays_number}Please send a Thanks message to {links}'
            suggested_messages = generate_thnx_for_connection_msg(row)
        else:
            keyboard = [
                [
                    InlineKeyboardButton("Request", callback_data=f"request_{index}_{user}_{done_today + 1}"),
                    InlineKeyboardButton("More Info", callback_data=f"moreInfo_{index}_{user}_{done_today + 1}"),
                    InlineKeyboardButton("Not TA", callback_data=f"notTA_{index}_{user}_{done_today + 1}"),
                    InlineKeyboardButton("Skip", callback_data=f"skip_{index}_{user}_{done_today + 1}")
                ]
            ]
            message = f'{todays_number}Please send an M0 message to {links}'
            suggested_messages = [suggested_outreach]

        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await self.application.bot.send_message(chat_id=self.users_to_send[user], text=message, parse_mode='HTML', reply_markup=reply_markup)
            if suggested_messages and suggested_messages[0]:
                for suggested_outreach in suggested_messages:
                    await self.application.bot.send_message(chat_id=self.users_to_send[user],text=suggested_outreach)
        except Exception as e:
            print(f"Error sending message to {user}: {e}")

    async def handle_callback(self, update, context):
        query = update.callback_query
        try:
            await query.answer()
        except Exception as e:
            print(f"Error answering callback query: {e}")
        try:
            data = query.data
            btn, index_str, user, todays_number = data.split("_")
            index = int(index_str)
            todays_number = int(todays_number)
            current_message_text = query.message.text
            row = self.leads_df.iloc[index]
            linkedin_profile = row['LinkedIn Profile']
            last_name = row['Last Name']
            links = f'<a href="{linkedin_profile}">{last_name}</a> - <a href="https://docs.google.com/spreadsheets/d/1ksKFLOutQZI4MgQxvodqeAuHBri5IYQVPTFXXd1SyXo/edit?gid=404358083#gid=404358083&range={index + 2}:{index + 2}">LeadGen</a>'
            if btn == "skip":
                self._add_skipped_lead(user, index)
                new_message = f"{links} was just skipped."
                await query.edit_message_text(text=new_message, parse_mode='HTML')
            else:
                today = datetime.now().strftime("%Y-%m-%d %a")
                if btn == "thanks":
                    lead_status = "Thanks message"
                elif btn in ["request", "moreInfo", "notTA"]:
                    if btn == "request":
                        lead_status = "Request"
                    elif btn == "moreInfo":
                        lead_status = "More Information"
                    elif btn == "notTA":
                        lead_status = "Не ЦА"
                    write_value_to_cell(value=today,
                                        sheet_name="Leads CRM", cell_range=f"{self.columns_letters[f'M0 {user}']}{index + 2}",
                                        spreadsheet_env_name='ΛV_LINKEDIN_LEADGEN_SPREADSHEET_ID')
                write_value_to_cell(value=today,
                                    sheet_name="Leads CRM",
                                    cell_range=f"{self.columns_letters[f'Datetime of the last touch {user}']}{index + 2}",
                                    spreadsheet_env_name='ΛV_LINKEDIN_LEADGEN_SPREADSHEET_ID')
                write_value_to_cell(lead_status,
                                    sheet_name="Leads CRM", cell_range=f"{self.columns_letters[f'Статус ліда ({user})']}{index + 2}",
                                    spreadsheet_env_name='ΛV_LINKEDIN_LEADGEN_SPREADSHEET_ID')
                prefix = f"{todays_number}/{self.number_of_leads_for_a_day} ({index + 2}/{len(self.leads_df)}) "
                new_message = f"{prefix}Status for {links} updated to '{lead_status}'."
                await query.edit_message_text(text=new_message, parse_mode='HTML')
                self.leads_df.at[index, f"Статус ліда ({user})"] = lead_status

                self._update_processed_lead(user)

            await self.send_next_message(user)
        except ValueError as e:
            print(f"Error parsing index from callback data: {e}")
            await query.edit_message_text(text=f"Error parsing index.")
        except Exception as e:
            print(f"Error handling callback: {e}")
            await query.edit_message_text(text=f"Error: {e}")

    async def remind_to_send_message(self):
        self._update_in_cache_leads_df()
        for user in self.users_to_send:
            await self.send_next_message(user)

    def _update_in_cache_leads_df(self):
        columns = ["First Name", "Last Name", "LinkedIn Profile", "Статус ліда (Juras)",
                   "Статус ліда (Andrus)", "M0 Andrus", "Datetime of the last touch Andrus",
                   "Company Name", "Company Desc",
                   "Founded", "Company size", "Company location / relevant office", "Company Motto",
                   "Suggested Outreach", 'Why Relevant Now', 'Signals']
        self.leads_df = read_specific_columns(columns_to_extract=columns, sheet_name="Leads CRM",
                                              spreadsheet_env_name='ΛV_LINKEDIN_LEADGEN_SPREADSHEET_ID')
        columns_to_extract = []
        for user in self.users_to_send:
            columns_to_extract.append(f"Статус ліда ({user})")
            columns_to_extract.append(f"M0 {user}")
            columns_to_extract.append(f"Datetime of the last touch {user}")
        self.columns_letters = get_column_letters(columns_to_extract, "Leads CRM",
                                                  spreadsheet_env_name='ΛV_LINKEDIN_LEADGEN_SPREADSHEET_ID')

    def register_handlers(self, application):
        application.add_handler(CallbackQueryHandler(self.handle_callback))


leadgen_reminder = LeadGenReminder()

