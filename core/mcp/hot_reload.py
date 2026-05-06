import signal
import os
import logging

def reload_handler(signum, frame):
    logging.info("Hot-reload signal received. Reloading skills...")
    # Trigger registry update logic here
    
signal.signal(signal.SIGUSR1, reload_handler)
