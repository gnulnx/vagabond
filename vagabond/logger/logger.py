#!/usr/bin/env python
import logging
import logging.config

from logutils.colorize import ColorizingStreamHandler

class ColorHandler(ColorizingStreamHandler):
    def __init__(self, *args, **kwargs):
        super(ColorHandler, self).__init__(*args, **kwargs)
        self.level_map = {
                # Logger : bg, fg, bold
                logging.DEBUG: (None, 'blue', False),
                logging.INFO: (None, 'green', False),
                logging.WARNING: (None, 'yellow', False),
                logging.ERROR: (None, 'red', False),
                logging.CRITICAL: ('red', 'white', True),
        }

#TODO: Provide option to turn off coloring in case user has a schema that doesn't work with our defaults
CONFIG = {
    'version':1,
    'disable_existing_loggers': True,
    'handlers':{
        'console': {
            'class':'vagabond.logger.logger.ColorHandler',
            #'class':'logging.StreamHandler',
            'info':'white',
            'level': 'DEBUG',
            'formatter': 'detailed',
            'stream': 'ext://sys.stdout',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'formatter': 'detailed',
            'filename': '/tmp/junk.log',
            'mode': 'a',
            'maxBytes': 10485760,
            'backupCount': 5,
        },
    },
    'formatters': {
        'detailed': {   
            'format': '%(asctime)s %(module)s line:%(lineno)-4d %(levelname)-8s %(message)s',
        },
        'normal':{
            'format':'%(asctime)s - %(levelname)s - %(message)s',
        }
    },
    'loggers': {
        'info': {
            'level':'DEBUG',
            'handlers':['console'],
        },
        'debug':{
            'level':'DEBUG',
            'handlers':['console'],
        },
    },
}

def get_logger(name=None):
    logging.config.dictConfig(CONFIG)
    L = logging.getLogger(name if name else 'debug')
    return L
