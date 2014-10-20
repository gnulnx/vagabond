#!/usr/bin/env python
import logging
import logging.config
from logutils import colorize

BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

#The background is set with 40 plus the number of the color, and the foreground with 30

#These are the sequences need to get colored ouput
RESET_SEQ = "\033[0m"
COLOR_SEQ = "\033[1;%dm"
BOLD_SEQ = "\033[1m"

def formatter_message(message, use_color = True):
    if use_color:
        message = message.replace("$RESET", RESET_SEQ).replace("$BOLD", BOLD_SEQ)
    else:
        message = message.replace("$RESET", "").replace("$BOLD", "")
    return message

COLORS = {
    'WARNING': YELLOW,
    'INFO': WHITE,
    'DEBUG': BLUE,
    'CRITICAL': YELLOW,
    'ERROR': RED
}

class ColoredFormatter(logging.Formatter):
    def __init__(self, msg, use_color = True):
        logging.Formatter.__init__(self, msg)
        self.use_color = use_color

    def format(self, record):
        levelname = record.levelname
        if self.use_color and levelname in COLORS:
            levelname_color = COLOR_SEQ % (30 + COLORS[levelname]) + levelname + RESET_SEQ
            record.levelname = levelname_color
        return logging.Formatter.format(self, record)

# Custom logger class with multiple destinations
class ColoredLogger(logging.Logger):
    FORMAT = "[$BOLD%(name)-20s$RESET][%(levelname)-18s]  %(message)s ($BOLD%(filename)s$RESET:%(lineno)d)"
    COLOR_FORMAT = formatter_message(FORMAT, True)
    def __init__(self, name=__name__):
        logging.Logger.__init__(self, name, logging.DEBUG)                

        color_formatter = ColoredFormatter(self.COLOR_FORMAT)

        console = logging.StreamHandler()
        console.setFormatter(color_formatter)

        self.addHandler(console)
        return

from logutils.colorize import ColorizingStreamHandler

class ColorHandler(ColorizingStreamHandler):
    def __init__(self, *args, **kwargs):
        super(ColorHandler, self).__init__(*args, **kwargs)
        self.level_map = {
                logging.DEBUG: (None, 'blue', False),
                logging.INFO: (None, 'green', False),
                logging.WARNING: (None, 'yellow', False),
                logging.ERROR: (None, 'red', False),
                logging.CRITICAL: ('red', 'white', True),
        }

CONFIG = {
    'version':1,
    'disable_existing_loggers': True,
    'handlers':{
        'console': {
            'class':'vagabond.logger.logger.ColorHandler',
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
