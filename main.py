import asyncio

import pandas as pd
import warnings

from src.bot.authorization import auth_manager
from src.bot.bot import application

warnings.simplefilter(action='ignore', category=pd.errors.SettingWithCopyWarning)
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=RuntimeWarning)

# from src.bot.bot import application
from src.schedule import setup_scheduler

async def shutdown(application, auth_manager, scheduler):
    print('Shutting down gracefully...')
    await auth_manager.reset_authorized_users()
    scheduler.shutdown()
    await application.shutdown()
    print('Shutdown complete')

def main():
    scheduler = setup_scheduler()
    try:
        application.run_polling()
    except KeyboardInterrupt:
        asyncio.run(shutdown(application, auth_manager, scheduler))

if __name__ == '__main__':
    from src.leadgen.leadgen_reminder import remind_to_send_message
    remind_to_send_message()
    main()