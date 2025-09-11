import os
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from telegram import Update
from telegram.ext import ContextTypes

load_dotenv()

from src.logger import logger

TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'configs', os.getenv('GOOGLE_OAUTH_CURRENT_TOKEN_FILE'))
SCOPES = ['https://www.googleapis.com/auth/drive']

def load_credentials() -> Credentials | None:
    """Loads a user's credentials from their token file if it exists."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    # If credentials exist but are expired, and a refresh token is present, refresh them.
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())  # Request object is not needed for user account flows
            save_credentials(creds)  # Save the refreshed credentials
        except Exception as e:
            logger.error(f"Failed to refresh token: {e}")
            raise ConnectionError("Please contact @AndrusKr to authorize disk")
    if creds and creds.valid:  # Check after token update
        return creds
    return None

def save_credentials(creds: Credentials):
    """Saves a user's credentials to their token file."""
    with open(TOKEN_FILE, 'w') as token_file:
        token_file.write(creds.to_json())
    logger.info(f"Saved new GOOGLE_OAUTH_CURRENT_TOKEN_FILE with name {os.getenv('GOOGLE_OAUTH_CURRENT_TOKEN_FILE')}")

async def start_google_drive_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the Google Drive authorization process."""
    try:
        CLIENT_SECRETS_FILE = f"configs/{os.getenv('CLIENT_SECRETS_FILE')}"
        # Инициализируем OAuth 2.0 процесс
        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            SCOPES
        )
        flow.redirect_uri = os.getenv("GOOGLE_OAUTH_REDIRECT_URI")
        auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
        # Initialize the OAuth 2.0 process
        context.user_data['oauth_flow'] = flow
        # Send instructions to the user
        instructions = (
            "Welcome! To upload files to your Google Drive, please authorize this bot.\n\n"
            "1. Click the link below to open the Google authorization page.\n"
            f"🔗 [Authorize with Google]({auth_url})\n\n"
            "2. After authorizing, you will be redirected to a page that might say 'This site can’t be reached'. "
            "**This is expected.** or you might see list of files and folders in the working directory\n\n"
            "3. **Copy the entire URL** from your browser's address bar.\n\n"
            "4. Paste the full URL back into this chat and send it to me."
        )
        await update.message.reply_text(instructions, parse_mode='Markdown', disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"Error starting Google Drive auth: {e}")
        await update.message.reply_text(f"Error starting Google Drive authorization: {e}.")


async def handle_oauth_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes the user's response with an authorization code."""
    if 'oauth_flow' not in context.user_data:
        await update.message.reply_text(
            "⚠️ Please start the authorization process with the 'disk' command first."
        )
        return
    try:
        flow = context.user_data['oauth_flow']
        authorization_response = update.message.text
        # Get the token
        flow.fetch_token(authorization_response=authorization_response)
        creds = flow.credentials
        # Save the token
        save_credentials(creds)
        # Remove the flow object from the context
        del context.user_data['oauth_flow']
        await update.message.reply_text("✅ Google Drive authorization was successful! Now you can upload files.")
    except Exception as e:
        logger.error(f"Error during OAuth callback: {e}")
        await update.message.reply_text(f"Error during OAuth callback: {e}")

