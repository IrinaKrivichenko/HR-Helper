import asyncio
import pandas as pd
import warnings
from telegram import Bot

from src.bot.authorization import auth_manager
from src.bot.bot import application

from dotenv import load_dotenv
load_dotenv()
import os

warnings.simplefilter(action='ignore', category=pd.errors.SettingWithCopyWarning)
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=RuntimeWarning)

# from src.bot.bot import application
from src.schedule import setup_scheduler

async def shutdown(application, auth_manager, scheduler):
    print('Shutting down gracefully...')
    bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
    if hasattr(auth_manager, 'application'):
        auth_manager.application.bot = bot
    try:
        await auth_manager.reset_authorized_users()
    except Exception as e:
        print(f"Error during shutdown: {e}")
    finally:
        scheduler.shutdown()
        await application.shutdown()
        print('Shutdown complete')

def main():
    scheduler = setup_scheduler()
    try:
        application.run_polling()
        print("after application.run_polling()")
    except KeyboardInterrupt:
        print("KeyboardInterrupt")
        asyncio.run(shutdown(application, auth_manager, scheduler))
    finally:
        print("finally")
        asyncio.run(shutdown(application, auth_manager, scheduler))

if __name__ == '__main__':
    main()