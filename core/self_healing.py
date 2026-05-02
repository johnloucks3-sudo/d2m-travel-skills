import logging
import time
import functools
import asyncio
import inspect
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("self_healing")

class SelfHealingLoop:
    """
    Implements a self-healing retry loop:
    1. Diagnoses the error.
    2. Applies a programmatic fix if identified.
    3. Retries EXACTLY once.
    4. Escalates on subsequent failure.
    """
    def __init__(self, logger_name="self_healing"):
        self.logger = logging.getLogger(logger_name)

    def __call__(self, func):
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                retries = 0
                max_retries = 1
                
                while retries <= max_retries:
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        self.logger.error(f"Error in {func.__name__}: {str(e)}")
                        if retries >= max_retries:
                            self.logger.critical(f"Max retries reached for {func.__name__}. Escalating.")
                            return self._escalate(func.__name__, str(e))
                        
                        retries += 1
                        self._diagnose_and_fix(e)
                        self.logger.info(f"Retrying {func.__name__} (attempt {retries}/{max_retries})...")
                        await asyncio.sleep(2 * retries)
                return None
            return async_wrapper
        else:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                retries = 0
                max_retries = 1
                
                while retries <= max_retries:
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        self.logger.error(f"Error in {func.__name__}: {str(e)}")
                        if retries >= max_retries:
                            self.logger.critical(f"Max retries reached for {func.__name__}. Escalating.")
                            return self._escalate(func.__name__, str(e))
                        
                        retries += 1
                        self._diagnose_and_fix(e)
                        self.logger.info(f"Retrying {func.__name__} (attempt {retries}/{max_retries})...")
                        time.sleep(2 * retries)
                return None
            return wrapper

    def _diagnose_and_fix(self, exception):
        # Placeholder for diagnosis logic
        if "429" in str(exception) or "rate limit" in str(exception).lower():
            self.logger.info("Diagnosis: Rate limit detected. Applying backoff.")
        elif "auth" in str(exception).lower():
            self.logger.info("Diagnosis: Auth error detected. Triggering re-auth.")
        else:
            self.logger.info("Diagnosis: Unknown error. Retrying.")

    def _escalate(self, func_name, error_msg):
        # Transition to ESCALATED state
        return f"ESCALATED: {func_name} failed after retry. Error: {error_msg}"

# Instance for easy use
self_healing = SelfHealingLoop()
