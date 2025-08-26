import asyncio
from telegram import Update
from telegram.error import NetworkError

from src.bot.locks import send_lock
from src.logger import logger


async def send_message(update: Update, message: str):
    """
    Sends a long message by splitting it into chunks of 4096 characters,
    ensuring that each chunk ends at the last newline before the limit.

    Args:
    - update (Update): The update object from the telegram bot.
    - message (str): The long message to be sent.
    """
    max_length = 4096
    start = 0
    # Using blocking to prevent simultaneous sending of messages
    message = str(message)
    async with send_lock:
        while start < len(message):
            # Find the last newline before the max_length limit
            end = min(start + max_length, len(message))
            last_newline = message.rfind('\n\n', start, end)

            # If no newline is found, send up to max_length characters
            if last_newline == -1:
                last_newline = end

            # Extract the chunk and send it
            chunk = message[start:last_newline].strip()

            # Check if the chunk is empty or only contains whitespace
            if not chunk:
                start = last_newline + 1
                continue
            try:
                await update.message.reply_text(chunk, parse_mode='HTML')
            except NetworkError as e:
                logger.error(f"NetworkError: {e}")
                # Try again after some time
                await asyncio.sleep(5)
                continue
            except Exception as e:
                logger.error(f"Exception: {e}")
                break

            # Update the start index
            start = last_newline + 1


