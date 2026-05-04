import logging
import sys

def setup_logger():
    logger = logging.getLogger("Geopulse")
    logger.setLevel(logging.INFO)
    
    fh = logging.FileHandler("error.log")
    fh.setLevel(logging.ERROR)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger

logger = setup_logger()
