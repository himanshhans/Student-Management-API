import logging
from app.utils.db_log_handler import DatabaseLogHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler(),
        DatabaseLogHandler()
    ]
)

logger = logging.getLogger("student_api")