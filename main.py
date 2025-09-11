import asyncio
import threading

import pandas as pd
import warnings
warnings.simplefilter(action='ignore', category=pd.errors.SettingWithCopyWarning)
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=RuntimeWarning)

from src.bot.bot import application
from src.schedule import setup_scheduler



def main() -> None:
    """Run the bot."""
    # Start the scheduler in a separate thread
    scheduler_thread = threading.Thread(target=setup_scheduler)
    scheduler_thread.daemon = True  # This makes the thread exit when the main program exits
    scheduler_thread.start()

    # Start the bot
    application.run_polling()


if __name__ == '__main__':
    main()

