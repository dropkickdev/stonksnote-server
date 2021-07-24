import os
from dotenv import load_dotenv

from .local import *
from .staging import *
from .production import *


class Settings:

    def __new__(cls, env: str):                                                      # noqa
        env = env.lower()
        if env in ['local', 'dev', 'development']:
            return LocalSettings()
        elif env == 'staging':
            return StagingSettings()
        else:
            return ProductionSettings()


load_dotenv(override=True)

ENV = os.getenv('ENV')
settings = Settings(ENV)