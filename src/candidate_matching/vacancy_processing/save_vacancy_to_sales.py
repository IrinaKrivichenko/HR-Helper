from telegram import Update
import re

from src.google_services.sheets import write_dict_to_sheet


def find_telegram_username_link(text):
    pattern = r'@(\w+)'
    match = re.search(pattern, text)
    if match:
        username = match.group(1)
        return f"t.me/{username}"
    else:
        return ""

def parse_candidates_from_answer(text):
    candidate_pattern = re.compile(
        r'(\d+)\.\s*<a\s+href=[\'"](https://docs\.google\.com/spreadsheets/d/.*?)[\'"]>(.*?)<\/a>.*?(?:🟥(.*?)🟨|$)',
        re.DOTALL
    )
    candidates = []
    for match in candidate_pattern.finditer(text):
        number = match.group(1)
        name = match.group(3).strip()
        link = match.group(2)
        ewr_text = match.group(4).strip()
        candidate_str = f"{number}. {name}"
        if ewr_text and ewr_text != "_":
            candidate_str += f" EWR {ewr_text}"
        candidate_str += f" {link}"
        candidates.append(candidate_str)
    return "\n".join(candidates)


def save_vacancy_to_sales(update: Update, vacancy_text: str, answer: str, keyword: str|None = None):
    if "Best-fit:" in answer and keyword is None:
            msg = update.message

            sales_cells_dict = {}
            sales_cells_dict["№"] = "=[№]3+1"
            sales_cells_dict['Дата'] = msg.date.strftime('%Y-%m-%d %a')
            sales_cells_dict['Хто занёс'] = f"t.me/{msg.chat.username}"

            if hasattr(msg.forward_origin, 'date'):
                msg_forward_origin_date = update.message.forward_origin.date
                origin_msg_date = msg_forward_origin_date.strftime('%Y-%m-%d %a')
                print(origin_msg_date)
                sales_cells_dict['Дата арыгіналу паведамленьня'] = origin_msg_date

            if hasattr(msg.forward_origin, 'sender_user_name'):
                sender_user_name = f"{msg.forward_origin.sender_user_name}\n"
            else:
                sender_user_name = f""
            if hasattr(msg.forward_origin, 'sender_user'):
                sender_user_username = msg.forward_origin.sender_user.username
                sender_user_link = f"t.me/{sender_user_username}"
            else:
                sender_user_link = find_telegram_username_link(vacancy_text)
            sales_cells_dict['Прадстаўнік замоўцы'] = f"{sender_user_name}{sender_user_link}"

            if hasattr(msg.forward_origin, 'message_id') and hasattr(msg.forward_origin, 'chat'):
                message_id = msg.forward_origin.message_id
                # chat_link = msg.forward_origin.chat.link
                chat_username = msg.forward_origin.chat.username
                message_link = f"t.me/{chat_username}/{message_id}"
                sales_cells_dict['Крыніца'] = message_link

            sales_cells_dict['Запыт'] = vacancy_text
            sales_cells_dict['Магчымыя кандыдаты на гэту заяўку падабраныя БОТАМ'] = parse_candidates_from_answer(answer)

            write_dict_to_sheet(data_dict=sales_cells_dict, spreadsheet_env_name="SALES_SPREADSHEET_ID", sheet_name="Запыты")
