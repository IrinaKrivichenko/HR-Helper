from telegram import Update

from src.google_services.sheets import write_dict_to_sheet


def save_vacancy_to_sales(update: Update, vacancy_text: str, candidates, keyword: str|None = None):
    if candidates and keyword is None:
            msg = update.message

            sales_cells_dict = {}
            sales_cells_dict["№"] = "=[№]3+1"

            if hasattr(msg.forward_origin, 'date'):
                msg_forward_origin_date = update.message.forward_origin.date
                origin_msg_date = msg_forward_origin_date.strftime('%Y-%m-%d %a')
                print(origin_msg_date)
                sales_cells_dict['Дата'] = origin_msg_date

            user_name = update.effective_user.link
            sales_cells_dict['Хто занёс'] = user_name

            if hasattr(msg.forward_origin, 'sender_user'):
                sender_user_link = msg.forward_origin.sender_user.link
                print(sender_user_link)
                # sender_user_username = msg.forward_origin.sender_user.username
                # print(sender_user_username)
                sales_cells_dict['Прадстаўнік замоўцы'] = sender_user_link

            if hasattr(msg.forward_origin, 'message_id') and hasattr(msg.forward_origin, 'chat'):
                message_id = msg.forward_origin.message_id
                chat_link = msg.forward_origin.chat.link
                # chat_username = msg.forward_origin.chat.username
                message_link = f"{chat_link}/{message_id}"
                print(message_link)
                sales_cells_dict['Крыніца'] = message_link

            sales_cells_dict['Запыт'] = vacancy_text
            import re
            candidates = re.sub(r' in spreadsheet row number \d+', '', candidates)
            sales_cells_dict['Магчымыя кандыдаты на гэту заяўку падабраныя БОТАМ'] = candidates

            write_dict_to_sheet(data_dict=sales_cells_dict, spreadsheet_env_name="SALES_SPREADSHEET_ID", sheet_name="Запыты")
