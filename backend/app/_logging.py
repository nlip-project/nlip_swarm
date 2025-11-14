import logging

logger = logging.getLogger("Listener")

def log_to_console(level):
    logger.setLevel(level)

    console_handler = logging.StreamHandler()
    formatter = logging.Formatter('\033[94m%(asctime)s - %(levelname)s\033[0m - %(message)s',
                                  datefmt='%H:%M:%S')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)