



from dotenv import load_dotenv

from src.google_services.sheets import write_dict_to_sheet

load_dotenv()

# bot.py
from telegram import Update
from telegram.ext import filters, MessageHandler, ApplicationBuilder, ContextTypes, CommandHandler

import os

async def handle_forwarded(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_user = await context.bot.get_me()
    print(bot_user.name == '@ostlab_hr_bot')

    msg = update.message.forward_origin.sender_user_name



# https://t.me/belaiplatform/1496  "👥 Кланіраванне ..." from _
#     удалось выяснить
#     msg.forward_origin.chat.username = belaiplatform
#     msg.forward_origin.chat.message_id = 1496
#
# https://t.me/c/2442766780/1575/2363  "Hey-hey!🌞..." from ejikqueen
#     удалось выяснить
#     msg.forward_origin.sender_user.link = https://t.me/ejikqueen
#     msg.forward_origin.sender_user.username = ejikqueen
#
# https://t.me/c/3010920963/1/644 "Дарагая, дабранач" from AndrusKr
#     единственное что удалось выяснить про оригинальное сообщение
#     msg.forward_origin.sender_user_name = Λndruś Kryvičenka
#
# https://t.me/c/2482564467/649 "Я ў Кракаве" from AndrusKr
#     единственное что удалось выяснить про оригинальное сообщение
#     msg.forward_origin.sender_user_name = Λndruś Kryvičenka

    msg.chat.username
    msg.date
    sales_cells_dict = {}
    sales_cells_dict["№"] = "=[№]3+1"

    if hasattr(msg.forward_origin, 'date'):
        msg_forward_origin_date = update.message.forward_origin.date
        origin_msg_date = msg_forward_origin_date.strftime('%Y-%m-%d %a')
        print(origin_msg_date)
        sales_cells_dict['Дата'] = origin_msg_date

    user = update.effective_user
    user_name = user.username if user.username else user.first_name
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
        chat_username = msg.forward_origin.chat.username
        message_link = f"{chat_username}/{message_id}"
        print(message_link)
        sales_cells_dict['Крыніца'] = message_link

    write_dict_to_sheet(data_dict=sales_cells_dict, spreadsheet_env_name="SALES_SPREADSHEET_ID", sheet_name="Запыты")
    #
    # attrs_to_check = [
    #     #'CHANNEL', 'CHAT', 'HIDDEN_USER', 'USER',
    #     'message_id', 'sender_user']
    # for attr_name in attrs_to_check:
    #     if hasattr(msg.forward_origin, attr_name):
    #         attr_value = getattr(msg.forward_origin, attr_name)
    #         print(f"msg.forward_origin.{attr_name}: {attr_value}")
    #         print()
    #
    # msg_forward_origin = update.message.forward_origin
    # print("dir(msg.forward_origin)")
    # # print(len(dir(msg_forward_origin)))
    # # print(dir(msg_forward_origin))




BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.ALL, handle_forwarded))
app.run_polling()