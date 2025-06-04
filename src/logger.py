import logging
import sys
import boto3
from watchtower import CloudWatchLogHandler

def setup_logger():
    # Create a logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Create a console handler for output to the console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # Format messages
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)

    # Add the console handler to the logger
    logger.addHandler(console_handler)

    # Configure the boto3 client for CloudWatch Logs
    boto3_client = boto3.client('logs', region_name='eu-north-1')

    # Add a CloudWatch handler
    cw_handler = CloudWatchLogHandler(
        boto3_client=boto3_client,
        log_group_name='telegram-bot-logs',
        stream_name='TelegramBotWorker'
    )

    # Add the CloudWatch handler to the logger
    logger.addHandler(cw_handler)

    return logger

# Example usage
logger = setup_logger()
logger.info("This is a test log message.")
