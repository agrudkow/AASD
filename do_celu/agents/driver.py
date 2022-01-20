#
# do_celu
#
# Copyright 2022 Agenty 007
#

import json
from datetime import datetime
from logging import Logger
from time import sleep
from typing import Any, Dict, Optional

import aioxmpp
from spade import agent, quit_spade
from spade.message import Message

from do_celu.behaviours import BaseOneShotBehaviour, BaseCyclicBehaviour, BasePeriodicBehaviour
from do_celu.config import Config, get_config
from do_celu.context import get_logger
from do_celu.messages.driver import DriverDataTemplate, PathChangeTemplate
from do_celu.utils.job_exit_code import JobExitCode
from do_celu.utils.performatives import Performatives

LOGGER_NAME = get_config().DRIVER_LOGGER_NAME


class DriverAgent(agent.Agent):
    # Behaviours
    inform_driver_data: 'InformDriverData'
    subscribe_to_manager: 'SubscribeToManager'
    receive_request_driver_data: 'ReceiveRequestDriverData'
    receive_request_driver_data_template: DriverDataTemplate
    receive_inform_path_change: 'ReceiveInformPathChange'
    receive_inform_path_change_template: PathChangeTemplate
    # Agent state
    __capacity: int
    __current_path: Optional[Any] = None
    __geolocation: Dict[str, Any]

    _logger: Logger
    _config: Config

    def __init__(
        self,
        jid: str,
        password: str,
        capacity: int,
        geolocation: Dict[str, Any],
        verify_security: bool = False,
    ):
        super().__init__(jid, password, verify_security=verify_security)
        self._config = get_config()
        self._logger = get_logger(LOGGER_NAME)
        self.__capacity = capacity
        self.__geolocation = geolocation

    class InformDriverData(BaseOneShotBehaviour):
        agent: 'DriverAgent'

        def __init__(self,):
            super().__init__(LOGGER_NAME)

        async def on_start(self):
            self._logger.debug('InformDriverData running...')

        async def run(self):
            msg = Message(to=self._config.MANAGER_JID)
            # TODO: add correct message
            msg.set_metadata("performative", Performatives.INFORM)  # Set the "inform" FIPA performative
            msg.set_metadata("ontology", self._config.ONTOLOGY)  # Set the ontology of the message content
            msg.set_metadata("language", "JSON")  # Set the language of the message content
            msg.body = json.dumps(self.agent._get_state())

            try:
                await self.send(msg)
                self._logger.debug('Message send!')
            except Exception as e:
                self._logger.error(e)
                self.kill(JobExitCode.FAILURE)
                return

        async def on_end(self):
            self._logger.debug('InformDriverData ending...')
            self.exit_code = JobExitCode.SUCCESS

    class ReceiveRequestDriverData(BaseCyclicBehaviour):
        agent: 'DriverAgent'

        def __init__(self,):
            super().__init__(LOGGER_NAME)

        async def on_start(self):
            self._logger.debug('ReceiveRequestDriverData running...')

        async def run(self):
            msg = await self.receive()
            if msg:
                self._logger.debug(f'Message received with content: {msg.body}')
                if not self.agent.has_behaviour(self.agent.inform_driver_data):
                    self._logger.debug('InformDriverData renewed')
                    await self.agent._setup_inform_driver_data()
                    self.agent.add_behaviour(self.agent.inform_driver_data)

        async def on_end(self):
            self._logger.debug('ReceiveRequestDriverData ending...')

    class ReceiveInformPathChange(BaseCyclicBehaviour):
        agent: 'DriverAgent'

        def __init__(self,):
            super().__init__(LOGGER_NAME)

        async def on_start(self):
            self._logger.debug('ReceiveInformPathChange running...')

        async def run(self):
            msg = await self.receive()
            if msg:
                self._logger.debug(f'Message received with content: {msg.body}')
                body = json.loads(msg.body)
                path = body['path']
                self._logger.debug(f'New path: {path}')
                self.agent.set_current_path(path)

        async def on_end(self):
            self._logger.debug('ReceiveInformPathChange ending...')

    class SubscribeToManager(BasePeriodicBehaviour):
        agent: 'DriverAgent'

        def __init__(
            self,
            period: float,
            start_at: Optional[datetime] = None,
        ):
            super().__init__(period, logger_name=LOGGER_NAME, start_at=start_at)

        async def on_start(self):
            self._logger.debug('SubscribeToManager running...')
            self.agent.presence.on_subscribe = self.on_subscribe
            self.agent.presence.on_subscribed = self.on_subscribed

        async def run(self):
            self._logger.info(f'test {self.presence.get_contacts()}')
            manager_jid = aioxmpp.JID.fromstr(self.agent._config.MANAGER_JID)
            if manager_jid not in self.agent.presence.get_contacts() \
                or self.agent.presence.get_contact(manager_jid).get('subscription', None) == 'none':
                self.agent.presence.unsubscribe(self.agent._config.MANAGER_JID)
                self._logger.info(f'{self.agent._config.MANAGER_JID} have not accepted subscription.')
                self._logger.info(f'Subscribing to {self._config.MANAGER_JID}.')
                self.agent.presence.subscribe(self.agent._config.MANAGER_JID)

        async def on_end(self):
            self._logger.debug('SubscribeToManager ending...')

        def on_subscribe(self, jid: str):
            self._logger.info(f'Agent {jid} asked for subscription.')
            if jid == self._config.MANAGER_JID:
                self.presence.approve(jid)
                self.presence.subscribe(jid)

        def on_subscribed(self, jid: str):
            self._logger.info(f'Agent {jid} accepted subscription.')

    async def setup(self):
        self._logger.info('DriverAgent started')
        await self._setup_receive_request_driver_data()
        await self._setup_receive_inform_path_change()
        await self._setup_inform_driver_data()
        await self._setup_subscribe_to_manager()
        self.add_behaviour(self.receive_request_driver_data, self.receive_request_driver_data_template)
        self.add_behaviour(self.receive_inform_path_change, self.receive_inform_path_change_template)
        self.add_behaviour(self.subscribe_to_manager)

    def set_current_path(self, path: Any):
        self.__current_path = path

    async def _setup_receive_request_driver_data(self):
        self.receive_request_driver_data_template = DriverDataTemplate()
        self.receive_request_driver_data = self.ReceiveRequestDriverData()

    async def _setup_receive_inform_path_change(self):
        self.receive_inform_path_change_template = PathChangeTemplate()
        self.receive_inform_path_change = self.ReceiveInformPathChange()

    async def _setup_inform_driver_data(self):
        self.inform_driver_data = self.InformDriverData()

    async def _setup_subscribe_to_manager(self):
        self.subscribe_to_manager = self.SubscribeToManager(period=self._config.DRIVER_SUBSCRITPION_CHECK_PERIOD)

    def _get_state(self) -> Dict[str, Any]:
        return {
            'capacity': self.__capacity,
            'current_path': self.__current_path,
            'geolocation': self.__geolocation,
        }


if __name__ == '__main__':
    config = get_config()
    logger = get_logger(config.DRIVER_LOGGER_NAME)
    driver = DriverAgent(
        config.DRIVER_JID,
        config.DRIVER_PASSWORD,
        capacity=50,
        geolocation={
            'x': 52.21905021340178,
            'y': 21.011905061692943,
        },
    )
    driver1 = DriverAgent(
        config.DRIVER1_JID,
        config.DRIVER_PASSWORD,
        capacity=50,
        geolocation={
            'x': 52.21905021340178,
            'y': 21.011905061692943,
        },
    )

    future = driver.start()
    future1 = driver1.start()
    future.result()
    future1.result()

    while driver.is_alive():
        try:
            sleep(1)
        except KeyboardInterrupt:
            break

    driver.stop()
    driver1.stop()
    logger.debug('Driver agent stopped')
    quit_spade()
