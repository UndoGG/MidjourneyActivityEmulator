import click
import yaml
from rich.logging import RichHandler
import logging

logging.getLogger('aiocache').setLevel('INFO')
logging.getLogger('tortoise').setLevel('INFO')
logging.getLogger('socketio').setLevel('INFO')
logging.getLogger('fastapi').setLevel('INFO')
logging.getLogger('aiohttp').setLevel('INFO')
logging.getLogger('pyrogram').setLevel('INFO')
logging.getLogger('aiosqlite').setLevel('INFO')
logging.getLogger('multipart').setLevel('INFO')
logging.getLogger('telethon').setLevel('INFO')
logging.getLogger('watchfiles').setLevel('INFO')

with open('config.yml') as f:
    config = yaml.safe_load(f)
    level = config.get("log_level", "DEBUG")

logging.basicConfig(
    level=level,
    format='',
    datefmt="[%X]",
    handlers=[
        RichHandler(rich_tracebacks=True, tracebacks_suppress=[click], omit_repeated_times=False, markup=True)]
)

logger = logging.getLogger("rich")

all_loggers = logging.Logger.manager.loggerDict.keys()
logger.debug(f'[cyan]Loggers: {list(all_loggers)}')

level_to_color = {
    "DEBUG": "cyan",
    "INFO": "green",
    "WARNING": "yellow",
    "ERROR": "red",
    "CRITICAL": "bold red"
}


class Formatter(logging.Formatter):
    def __init__(self, prefix: str):
        self.prefix = prefix
        self.datefmt = "[%X]"
        self._style = logging.PercentStyle(fmt="")

    def format(self, record):
        levelname = record.levelname
        color = level_to_color.get(levelname, "white")
        formatted = "{prefix}: {message}".format(
            color=color, levelname=levelname, message=record.getMessage(), prefix=self.prefix
        )
        return formatted


def reg_logger(prefix, log_level=level) -> logging.Logger:
    handler = RichHandler(rich_tracebacks=True, tracebacks_suppress=[click], omit_repeated_times=False, markup=True)
    handler.setFormatter(Formatter(prefix))

    logger = logging.Logger(prefix, level=log_level)
    logger.addHandler(handler)
    return logger
