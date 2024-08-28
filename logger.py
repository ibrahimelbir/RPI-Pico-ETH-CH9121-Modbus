import logging

logger = logging.getLogger(__name__)

logger.setLevel(logging.DEBUG)

error_handler = logging.FileHandler("error.log", mode="w")
debug_handler = logging.FileHandler("debug.log", mode="w")

error_handler.setLevel(logging.ERROR)
debug_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter("[%(levelname)s][%(asctime)s] : %(message)s")

error_handler.setFormatter(formatter)
debug_handler.setFormatter(formatter)

logger.addHandler(error_handler)
logger.addHandler(debug_handler)