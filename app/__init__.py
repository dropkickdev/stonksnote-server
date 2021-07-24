import logging, pytz
from datetime import datetime
from fastapi.logger import logger

from .exceptions import *
from .settings import *
from .cache import *

from icecream.icecream import IceCreamDebugger
from app.settings import settings as s



# Icecream
ic = IceCreamDebugger()
ic.enabled = s.DEBUG


# # This works, just commenting out for now. Put it back later.
# Logger
tz = pytz.timezone('Asia/Manila')
filename = datetime.now(tz=tz).strftime(f'{s.APPCODE.upper()}:{s.ENV.lower()}-%Y-%m-%d')

file_handler = logging.FileHandler(f'logs/{filename}.log')
file_format = '[%(asctime)s] %(levelname)s %(funcName)s:%(lineno)d: %(message)s'
file_handler.setFormatter(logging.Formatter(file_format))
logger.addHandler(file_handler)

# if s.DEBUG:
#     stream_handler = logging.StreamHandler()
#     stream_format = '%(levelname)s %(funcName)s:%(lineno)d: %(message)s'
#     stream_handler.setFormatter(logging.Formatter(stream_format))
#     stream_handler.setLevel(logging.INFO)
#     logger.addHandler(stream_handler)





