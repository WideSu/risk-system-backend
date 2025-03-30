from functools import wraps
import logging

# Setup logger
logger = logging.getLogger(__name__)

def log_function(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        logger.info(f"Executing {func.__name__} with arguments: {args}, {kwargs}")
        try:
            # Await the async function's result
            result = await func(*args, **kwargs)
            logger.info(f"{func.__name__} completed successfully with result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            raise
    return wrapper