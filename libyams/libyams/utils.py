import yaml

from wrapt import synchronized

import logging
logger = logging.getLogger(__name__)

_cur_conf = None


@synchronized
def get_conf(filename="config.yml"):
    global _cur_conf

    if not _cur_conf:
        with open(filename) as file:
            _cur_conf = yaml.load(file)

    logger.info("config loaded")

    return _cur_conf
