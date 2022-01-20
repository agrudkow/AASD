#
# do_celu
#
# Copyright 2022 Agenty 007
#

import logging
from functools import lru_cache
from typing import Union

from pydantic import BaseSettings


class Config(BaseSettings):
    ONTOLOGY: str = 'DoCeluMainOntology'
    LOG_LEVEL: Union[int, str] = logging.INFO
    # Driver
    DRIVER_LOGGER_NAME: str = 'driver_agent'
    DRIVER_JID: str
    DRIVER1_JID: str
    DRIVER_PASSWORD: str
    DRIVER_SUBSCRITPION_CHECK_PERIOD: float = 10.
    # Manager
    MANAGER_LOGGER_NAME: str = 'manager_agent'
    MANAGER_JID: str
    MANAGER_PASSWORD: str
    # Client
    CLIENT_LOGGER_NAME: str = 'client_agent'
    CLIENT_JID: str
    CLIENT_PASSWORD: str
    # Mathematician
    MATHEMATICIAN_LOGGER_NAME: str = 'mathematician_agent'
    MATHEMATICIAN_JID: str
    MATHEMATICIAN_PASSWORD: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_config():
    return Config()
