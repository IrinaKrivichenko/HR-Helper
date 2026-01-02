import json
from pathlib import Path
import re
import locale
from datetime import datetime, date

import pandas as pd
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

from src.data_processing.date_parser import days_since
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
        self.status_doses = {
            "": {"dose": 15, "days_since": None},
            "Request": {"dose": 5, "days_since": 30},
            "Contact": {"dose": 5, "days_since": None},
            "Thanks message": {"dose": 5, "days_since": 14}
        }
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
                "processed_counts": {user: {status: 0 for status in self.status_doses} for user in
                                     self.users_to_send.keys()},
                "skipped_indices": {user: [] for user in self.users_to_send.keys()}
            }
            return initial_data
        with open(file_path, "r") as f:
            data = json.load(f)
        return data

    def _update_processed_lead(self, user, status):
        file_path = self._get_today_file_path()
        data = self._read_processed_leads()
        data["processed_counts"][user][status] += 1
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
        processed_counts = data["processed_counts"].get(user, {})
        total_processed = sum(processed_counts.get(status, 0) for status in self.status_doses)
        skipped_indices = data["skipped_indices"].get(user, [])
        today = date.today()

        for status, config in self.status_doses.items():
            dose = config["dose"]
            days_condition = config["days_since"]
            if processed_counts.get(status, 0) >= dose:
                continue
            status_leads = self.leads_df[
                (self.leads_df[f"Статус ліда ({user})"] == status) &
                (self.leads_df["LinkedIn Profile"] != '') &
                (~self.leads_df.index.isin(skipped_indices))
                ]
            if not status_leads.empty:
                if status == "Contact":
                    # Для Contact: сортируем по дате последнего контакта (самые свежие первыми)
                    status_leads = status_leads.sort_values(
                        by=f"Datetime of the last touch {user}",
                        key=lambda x: x.apply(lambda s: days_since(s, today))
                    )
                if days_condition is not None:
                    for index, row in status_leads.iterrows():
                        last_touch = row[f"Datetime of the last touch {user}"]
                        if days_condition is None or days_since(last_touch, today) >= days_condition:
                            return row, total_processed
                else:
                    for index, row in status_leads.iterrows():
                        return row, total_processed
        return None, total_processed

    async def send_next_message(self, user):
        row, total_processed = await self.get_next_lead(user)
        number_of_leads_for_a_day = sum(self.status_doses[status]["dose"] for status in self.status_doses)
        if row is None:
            if total_processed >= number_of_leads_for_a_day:
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
        todays_number = f"{total_processed+1} of {number_of_leads_for_a_day}\n"
        links = f'<a href="{linkedin_profile}">{first_name} {last_name}</a> - <a href="https://docs.google.com/spreadsheets/d/1ksKFLOutQZI4MgQxvodqeAuHBri5IYQVPTFXXd1SyXo/edit?gid=404358083#gid=404358083&range={index+2}:{index+2}">LeadGen</a>'
        if row[f"Статус ліда ({user})"] == "":
            keyboard = [
                [
                    InlineKeyboardButton("Request", callback_data=f"request_{index}_{user}_{total_processed + 1}"),
                    InlineKeyboardButton("More Info", callback_data=f"moreInfo_{index}_{user}_{total_processed + 1}"),
                    InlineKeyboardButton("Not TA", callback_data=f"notTA_{index}_{user}_{total_processed + 1}"),
                    InlineKeyboardButton("Skip", callback_data=f"skip_{index}_{user}_{total_processed + 1}")
                ]
            ]
            message = f'{todays_number}Please send an M0 message to {links}'
            suggested_messages = [suggested_outreach]
        elif row[f"Статус ліда ({user})"] == "Request":
            keyboard = [
                [
                    InlineKeyboardButton("Withdrawn", callback_data=f"withdrawn_{index}_{user}_{total_processed + 1}"),
                    InlineKeyboardButton("Skip", callback_data=f"skip_{index}_{user}_{total_processed + 1}")
                ]
            ]
            message = f'{todays_number}Withdrawn from {links}'
            suggested_messages = []
        elif row[f"Статус ліда ({user})"] == "Contact":
            keyboard = [
                [
                    InlineKeyboardButton("Thanks message", callback_data=f"thanks_{index}_{user}_{total_processed + 1}"),
                    InlineKeyboardButton("Skip", callback_data=f"skip_{index}_{user}_{total_processed + 1}")
                ]
            ]
            message = f'{todays_number}Please send a Thanks message to {links}'
            suggested_messages = generate_thnx_for_connection_msg(row)
        elif row[f"Статус ліда ({user})"] == "Thanks message":
            keyboard = [
                [
                    InlineKeyboardButton("First outreach message", callback_data=f"m1_{index}_{user}_{total_processed + 1}"),
                    InlineKeyboardButton("Skip", callback_data=f"skip_{index}_{user}_{total_processed + 1}")
                ]
            ]
            message = f'{todays_number}Please send an First outreach message to {links}'
            suggested_messages = []

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
                    prev_status = "Contact"
                elif btn == "withdrawn":
                    lead_status = "Withdrawn"
                    prev_status = "Request"
                elif btn == "m1":
                    lead_status = "First outreach message"
                    prev_status = "Thanks message"
                elif btn == "request":
                    lead_status = "Request"
                    prev_status = ""
                elif btn == "moreInfo":
                    lead_status = "More Information"
                    prev_status = ""
                elif btn == "notTA":
                    lead_status = "Не ЦА"
                    prev_status = ""

                if row[f"M0 {user}"] == "":
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
                number_of_leads_for_a_day = sum(self.status_doses[status]["dose"] for status in self.status_doses)
                prefix = f"{todays_number}/{number_of_leads_for_a_day} ({index + 2}/{len(self.leads_df)}) "
                new_message = f"{prefix}Status for {links} updated to '{lead_status}'."
                await query.edit_message_text(text=new_message, parse_mode='HTML')
                self.leads_df.at[index, f"Статус ліда ({user})"] = lead_status

                self._update_processed_lead(user, prev_status)

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

