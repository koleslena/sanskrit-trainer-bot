import logging
import sys

# Настраиваем заново с принудительным выводом в stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(name)s | %(message)s",
    stream=sys.stdout, # Явно указываем поток, который видит Docker
    force=True
)

logger = logging.getLogger("SanskritMAS")
logger.info("🚀 Бот запускается...")