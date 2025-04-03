from loguru import logger

logger.add("logs/bank_statement_processor.log", rotation="1 MB")
