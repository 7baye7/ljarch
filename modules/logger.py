import logging
from logging import handlers
from modules.common import CreatePathIfNotExists

def SetupLogger(logFilePath, dateFormatString):
    logger = logging.getLogger('log')
    
    if not len(logger.handlers):
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        
        # create a console handler
        consoleHandler = logging.StreamHandler()
        consoleHandler.setLevel(logging.INFO)
        consoleHandler.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(consoleHandler)
                
        # create a file handler
        CreatePathIfNotExists(logFilePath)
        fileHandler = logging.handlers.TimedRotatingFileHandler(logFilePath, when = 'midnight', backupCount = 10, encoding = 'utf-8')
        fileHandler.setLevel(logging.DEBUG)
        fileHandler.setFormatter(logging.Formatter('[%(levelname)-8s: %(asctime)s - %(filename)s:%(lineno)s - %(funcName)s()] - %(message)s', dateFormatString))
        logger.addHandler(fileHandler)
    return logger
