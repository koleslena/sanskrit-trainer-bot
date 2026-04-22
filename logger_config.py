import logging
import sys


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(name)s | %(message)s",
    stream=sys.stdout, 
    force=True
)

logger = logging.getLogger("SanskritMAS")
logger.info("🚀 Бот запускается...")