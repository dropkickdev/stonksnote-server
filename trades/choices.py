from gettext import gettext as _
from enum import Enum


class TradeStatusChoices(str, Enum):
    PLAN = 'PLAN'
    LATE = 'LATE'
    REVISIT = 'REVISIT'


class ActionStatusChoices(str, Enum):
    BUY = 'BUY'
    SELL = 'SELL'
    WATCH = 'WATCH'
    CANCELLED = 'CANCELLED'
    