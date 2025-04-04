import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from loguru import logger

# Configure loguru logger
logger.remove()  # Remove default handler
logger.add(
    sys.stdout,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    level="INFO"
)
logger.add(
    "logs/app.log",
    rotation="10 MB",
    retention="30 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {module}:{line} | {message}",
    level="DEBUG"
)

# Create custom handler for standard library logging
class InterceptHandler(logging.Handler):
    def emit(self, record):
        # Get corresponding loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )

# Configure logging for third-party libraries
logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

# Configure specific loggers
for _log in ["uvicorn", "uvicorn.error", "fastapi"]:
    _logger = logging.getLogger(_log)
    _logger.handlers = [InterceptHandler()]

# Create logs directory if it doesn't exist
Path("logs").mkdir(exist_ok=True)