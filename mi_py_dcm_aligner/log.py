import logging, re, sys
from typing import Optional

import env

def setup_from_env() -> tuple[str, Optional[str]]:        
    log_level = env.get_or_ask_and_wait_for_param("LOG_LEVEL", default="info", value_type=str)
    log_filter = env.get_or_ask_and_wait_for_param("LOG_FILTER", default=None, value_type=str)
    setup(log_level, log_filter)    
    return log_level, log_filter

def setup( log_level:str, log_filter:Optional[str]=None ) -> None:
    
    # Set up basic logging
    log_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)  # Set global log level

    # Create and configure a StreamHandler for console output
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)

    # Add the handler to the root logger
    for handler in root_logger.handlers:
        root_logger.removeHandler( handler )
    root_logger.addHandler(console_handler)
    
    # Set up regex!
    if log_filter:
        class GlobalRegexFilter(logging.Filter):
            def __init__(self, pattern):
                super().__init__()
                self.pattern = re.compile(pattern)

            def filter(self, record):
                # Suppress log messages that match the regex
                return not self.pattern.search(record.getMessage())            
        root_logger.addFilter(GlobalRegexFilter(log_filter))
        
# initial setup   
     