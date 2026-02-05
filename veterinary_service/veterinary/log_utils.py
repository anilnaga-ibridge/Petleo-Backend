
import datetime
import os

LOG_FILE = "/Users/PraveenWorks/Anil Works/Petleo-Backend/veterinary_service/middleware_trace.log"

def log_debug(tag, msg):
    """
    Centralized logging for veterinary service context and permissions.
    """
    try:
        with open(LOG_FILE, "a") as f:
            timestamp = datetime.datetime.now().isoformat()
            f.write(f"{timestamp} - [{tag}] {msg}\n")
    except:
        pass

def log_perm(msg):
    log_debug("PERM", msg)

def log_mw(msg):
    log_debug("MW", msg)

def log_auth(msg):
    log_debug("AUTH", msg)
