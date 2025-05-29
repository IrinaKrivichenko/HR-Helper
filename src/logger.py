import logging
import sys

def setup_logger():
    logger = logging.getLogger()
    # Set the logging level
    logger.setLevel(logging.INFO)

    # Create a handler for output to the console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # Format messages
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)

    # Add a console_handler to the logger
    logger.addHandler(console_handler)

    return logger



logger = setup_logger()

