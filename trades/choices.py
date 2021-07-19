from gettext import gettext as _
from enum import Enum, IntEnum


class TradeStatusChoices(str, Enum):
    PLAN = 'PLAN'
    LATE = 'LATE'
    REVISIT = 'REVISIT'


class ActionStatusChoices(str, Enum):
    BUY = 'BUY'
    SELL = 'SELL'
    WATCH = 'WATCH'
    CANCELLED = 'CANCELLED'
    
class EquityCategoryChoices(IntEnum):
    STOCK = 1
    INDEX = 2
    FOREX = 3
    COMMODITY = 4
    CRYPTO = 5
    PREFERRED = 6