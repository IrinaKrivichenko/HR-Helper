import asyncio
from telegram import Update
from telegram.error import NetworkError

from src.bot.locks import send_lock

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
    async with send_lock:
        while start < len(message):
            # Find the last newline before the max_length limit
            end = min(start + max_length, len(message))
            last_newline = message.rfind('\n', start, end)

            # If no newline is found, send up to max_length characters
            if last_newline == -1:
                last_newline = end

            # Extract the chunk and send it
            chunk = message[start:last_newline].strip()
            try:
                await update.message.reply_text(chunk, parse_mode='HTML')
            except NetworkError as e:
                print(f"NetworkError: {e}")
                # Повторная попытка через некоторое время
                await asyncio.sleep(5)
                continue
            except Exception as e:
                print(f"Exception: {e}")
                break

            # Update the start index
            start = last_newline + 1


