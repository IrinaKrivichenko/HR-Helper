from datetime import datetime

import pandas as pd
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

from src.google_services.sheets import read_specific_columns, write_value_to_cell

class LeadGenReminder:

    number_of_leads_for_a_day =10

    def __init__(self):
        self.users_to_send = {"Andrus":  381735431}  # 694614399}
        self.application = None


    def set_application(self, application):
        self.application = application
        self.register_handlers(application)

    async def get_next_lead(self, user):
        columns = ["First Name", "Last Name", "LinkedIn Profile", "Industry", "Статус ліда (Andrus)", "M0 Andrus", "Статус ліда (Juras)"]
        leads_df = read_specific_columns(columns_to_extract=columns, sheet_name="Leads CRM", spreadsheet_env_name='ΛV_LINKEDIN_LEADGEN_SPREADSHEET_ID')
        today = datetime.now().strftime("%d-%m-%Y")
        done_today = leads_df[leads_df[f"M0 {user}"] == today].shape[0]
        if done_today >= LeadGenReminder.number_of_leads_for_a_day:
            return None, done_today
        filtered_leads = leads_df[(leads_df["Статус ліда (Juras)"] != "Не ЦА") & (leads_df["LinkedIn Profile"] != '')]
        user_filtered_leads = filtered_leads[(filtered_leads[f"Статус ліда ({user})"] == "")]
        if len(user_filtered_leads) == 0:
            return None, done_today
        for index, row in user_filtered_leads.iterrows():
            if row[f"M0 {user}"]=='':
                return row, done_today
        return None, done_today

    async def send_next_message(self, user):
        row, done_today = await self.get_next_lead(user)
        if row is None:
            if done_today >= LeadGenReminder.number_of_leads_for_a_day:
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
        last_name = row['Last Name']
        index = row.name
        todays_number = f"{done_today+1} of {LeadGenReminder.number_of_leads_for_a_day}\n"
        message = f'{todays_number}Please send an M0 message to <a href="{linkedin_profile}">{last_name}</a>'
        keyboard = [
            [
                InlineKeyboardButton("Done", callback_data=f"done_{index}_{last_name}"),
                InlineKeyboardButton("Not TA", callback_data=f"not_ta_{index}_{last_name}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await self.application.bot.send_message(
                chat_id=self.users_to_send[user],
                text=message,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        except Exception as e:
            print(f"Error sending message to {user}: {e}")

    async def handle_callback(self, update, context):
        query = update.callback_query
        try:
            await query.answer()
        except Exception as e:
            print(f"Error answering callback query: {e}")
        data = query.data
        try:
            if data.startswith("done_"):
                rest = data[len("done_"):]
                index_str, last_name = rest.split("_", 1)
                index = int(index_str)
                write_value_to_cell("Request", sheet_name="Leads CRM", cell_range=f"H{index + 2}", spreadsheet_env_name='ΛV_LINKEDIN_LEADGEN_SPREADSHEET_ID')
                write_value_to_cell(datetime.now().strftime("%d-%m-%Y"), sheet_name="Leads CRM", cell_range=f"I{index + 2}", spreadsheet_env_name='ΛV_LINKEDIN_LEADGEN_SPREADSHEET_ID')
                await query.edit_message_text(text=f"Status for {last_name} updated to 'Request'.")
                user = next(iter(self.users_to_send.keys()))
                await self.send_next_message(user)
            elif data.startswith("not_ta_"):
                rest = data[len("not_ta_"):]
                index_str, last_name = rest.split("_", 1)
                index = int(index_str)
                write_value_to_cell("Не ЦА", sheet_name="Leads CRM", cell_range=f"H{index + 2}",spreadsheet_env_name='ΛV_LINKEDIN_LEADGEN_SPREADSHEET_ID')
                await query.edit_message_text(text=f"Status for {last_name} updated to 'Не ЦА'.")
                user = next(iter(self.users_to_send.keys()))
                await self.send_next_message(user)
        except ValueError as e:
            print(f"Error parsing index from callback data: {e}")
            await query.edit_message_text(text=f"Error parsing index.")
        except Exception as e:
            print(f"Error handling callback: {e}")
            await query.edit_message_text(text=f"Error: {e}")

    async def remind_to_send_message(self):
        for user in self.users_to_send:
            await self.send_next_message(user)

    def register_handlers(self, application):
        application.add_handler(CallbackQueryHandler(self.handle_callback))

#
# class LeadGenReminder:
#
#     def __init__(self):
#         self.users_to_send = {"Andrus":  694614399}
#         self.application = None
#
#
#     def set_application(self, application):
#         self.application = application
#         self.register_handlers(application)
#
#     async def remind_to_send_message(self):
#         pass
#         columns = ["First Name", "Last Name", "LinkedIn Profile", "Industry", "Статус ліда (Andrus)", "M0 Andrus", "Статус ліда (Juras)"]
#         leads_df = read_specific_columns(columns_to_extract=columns, sheet_name="Leads CRM", spreadsheet_env_name='ΛV_LINKEDIN_LEADGEN_SPREADSHEET_ID')
#         print("len(leads_df)", len(leads_df))
#         filtered_leads = leads_df[(leads_df["Статус ліда (Juras)"] != "Не ЦА") & (leads_df["LinkedIn Profile"] != '') ]
#         print("len(filtered_leads)", len(filtered_leads))
#         print(filtered_leads["LinkedIn Profile"])
#         today = datetime.now().strftime("%d-%m-%Y")
#         for user in self.users_to_send:
#             done_today = leads_df[leads_df[f"M0 {user}"] == today].shape[0]
#             num_of_rows_to_do = 2 - done_today
#             user_filtered_leads = filtered_leads[(filtered_leads[f"Статус ліда ({user})"] == "")].head(num_of_rows_to_do)
#
#             for index, row in user_filtered_leads.iterrows():
#                 linkedin_profile = row['LinkedIn Profile']
#                 last_name = row['Last Name']
#                 message = f'Please send an M0 message to <a href="{linkedin_profile}">{last_name}</a>'
#                 keyboard = [
#                     [
#                         InlineKeyboardButton("Done", callback_data=f"done_{index}_{last_name}"),
#                         InlineKeyboardButton("Not TA", callback_data=f"not_ta_{index}_{last_name}")
#                     ]
#                 ]
#                 reply_markup = InlineKeyboardMarkup(keyboard)
#
#                 try:
#                     print(f"Sending message to {user}: {message}")
#                     await self.application.bot.send_message(
#                         chat_id=self.users_to_send[user],
#                         text=message,
#                         parse_mode='HTML',
#                         reply_markup=reply_markup
#                     )
#                 except Exception as e:
#                     print(f"Error sending message to {user}: {e}")
#
#     async def handle_callback(self, update, context):
#         query = update.callback_query
#
#         try:
#             await query.answer()
#         except Exception as e:
#             print(f"Error answering callback query: {e}")
#
#         data = query.data
#         try:
#             if data.startswith("done_"):
#                 parts = data.split("_", 2)  # Разбиваем строку на три части: префикс, индекс, фамилия
#                 index = int(parts[1])
#                 last_name = parts[2]
#                 write_value_to_cell("Request", sheet_name="Leads CRM", cell_range=f"H{index + 2}",
#                                     spreadsheet_env_name='ΛV_LINKEDIN_LEADGEN_SPREADSHEET_ID')
#                 write_value_to_cell(datetime.now().strftime("%d-%m-%Y"), sheet_name="Leads CRM",
#                                     cell_range=f"I{index + 2}",
#                                     spreadsheet_env_name='ΛV_LINKEDIN_LEADGEN_SPREADSHEET_ID')
#                 await query.edit_message_text(
#                     text=f"Status for {last_name} updated to 'Request' and date added to M0 column.")
#             elif data.startswith("not_ta_"):
#                 rest = data[len("not_ta_"):]
#                 index_str, last_name = rest.split("_", 1)
#                 index = int(index_str)
#                 write_value_to_cell("Не ЦА", sheet_name="Leads CRM", cell_range=f"H{index + 2}",
#                                     spreadsheet_env_name='ΛV_LINKEDIN_LEADGEN_SPREADSHEET_ID')
#                 await query.edit_message_text(text=f"Status for {last_name} updated to 'Не ЦА'.")
#         except ValueError as e:
#             print(f"Error parsing index from callback data: {e}")
#             await query.edit_message_text(text=f"Error parsing index.")
#         except Exception as e:
#             print(f"Error handling callback: {e}")
#             await query.edit_message_text(text=f"Error: {e}")
#
#     def register_handlers(self, application):
#         application.add_handler(CallbackQueryHandler(self.handle_callback))

leadgen_reminder = LeadGenReminder()

