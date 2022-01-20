#
# do_celu
#
# Copyright 2022 Agenty 007
#

import json
from datetime import datetime
from logging import Logger
from time import sleep
from typing import Optional, List

from spade import agent, quit_spade
from spade.message import Message

from do_celu.behaviours import BaseOneShotBehaviour
from do_celu.config import Config, get_config
from do_celu.context import get_logger
from do_celu.messages.client import BestConnectionsTemplate, ReservationAvailabilityTemplate, AcceptProposalTemplate
from do_celu.entities.connection import ConnectionRequest, Connection
from do_celu.utils.job_exit_code import JobExitCode
from do_celu.utils.performatives import Performatives

LOGGER_NAME = get_config().CLIENT_LOGGER_NAME


class ClientAgent(agent.Agent):
    # Behaviours:
    request_available_connections: 'RequestAvailableConnections'
    receive_inform_best_connections: 'ReceiveInformBestConnections'
    receive_inform_best_connections_template: 'BestConnectionsTemplate'
    receive_availability_for_reservation: 'ReceiveAvailabilityForReservation'
    receive_availability_for_reservation_template: 'ReservationAvailabilityTemplate'
    propose_chosen_connection: 'ProposeChosenConnection'
    receive_accept_proposal_client_path: 'ReceiveAcceptProposalClientPath'
    receive_accept_proposal_client_path_template: 'AcceptProposalTemplate'

    # Agent state:
    __start_date: datetime
    __origin: str
    __destination: str
    __best_connections: Optional[List[Connection]]
    __chosen_connection: Optional[Connection]
    __reservation_available: bool
    __connection_accepted: bool

    _logger: Logger
    _config: Config

    def __init__(self, jid: str, password: str, start_date: datetime, origin: str, destination: str):
        super().__init__(jid, password)
        self._config = get_config()
        self._logger = get_logger(LOGGER_NAME)
        self.__start_date = start_date
        self.__origin = origin
        self.__destination = destination
        self.__best_connections: Optional[List[Connection]] = None
        self.__chosen_connection: Optional[Connection] = None
        self.__reservation_available = False
        self.__connection_accepted = False

    class RequestAvailableConnections(BaseOneShotBehaviour):
        agent: 'ClientAgent'

        def __init__(self, ):
            super().__init__(LOGGER_NAME)

        async def on_start(self):
            self._logger.debug('RequestAvailableConnections running...')

        async def run(self):
            msg = Message(to=self._config.MANAGER_JID)
            msg.set_metadata("performative", Performatives.REQUEST)
            msg.set_metadata("ontology", self._config.ONTOLOGY)  # Set the ontology of the message content
            msg.set_metadata("language", "JSON")
            msg.body = json.dumps(self.agent._get_connection_request())

            try:
                await self.send(msg)
                self._logger.debug("Request for available connections sent!")
            except Exception as e:
                self._logger.error(e)
                self.kill(JobExitCode.FAILURE)
                return

        async def on_end(self):
            self._logger.debug('RequestAvailableConnections ending...')
            self.exit_code = JobExitCode.SUCCESS

    # there is no sense that it will be CyclicBehaviour, because of one-time information about available connections
    class ReceiveInformBestConnections(BaseOneShotBehaviour):
        agent: 'ClientAgent'

        def __init__(self, ):
            super().__init__(LOGGER_NAME)

        async def on_start(self):
            self._logger.debug('ReceiveInformBestConnections running...')

        async def run(self):
            await self.agent.request_available_connections.join()

            msg = await self.receive()
            if msg:
                self._logger.debug(f'Message received with content: {msg.body}')
                body = json.loads(msg.body)
                best_connections = body['best_connections']
                self.agent.set_best_connections(best_connections)

            self.kill()

        async def on_end(self):
            self._logger.debug('ReceiveInformBestConnections ending...')

    class ReceiveAvailabilityForReservation(BaseOneShotBehaviour):
        agent: 'ClientAgent'

        def __init__(self, ):
            super().__init__(LOGGER_NAME)

        async def on_start(self):
            self._logger.debug('ReceiveAvailabilityForReservation running...')

        async def run(self):
            await self.agent.request_available_connections.join()

            msg = await self.receive()
            if msg:
                self._logger.debug(f'Message received with content: {msg.body}')
                body = json.loads(msg.body)
                is_reservation_available = body['is_reservation_available']
                self.agent.set_reservation_available(is_reservation_available)

            self.kill()

        async def on_end(self):
            self._logger.debug('ReceiveAvailabilityForReservation ending...')

    class ProposeChosenConnection(BaseOneShotBehaviour):
        agent: 'ClientAgent'

        def __init__(self, ):
            super().__init__(LOGGER_NAME)

        async def on_start(self):
            self._logger.debug('ProposeChosenConnection running...')

        async def run(self):
            msg = Message(to=self._config.MANAGER_JID)
            msg.set_metadata("performative", Performatives.PROPOSE)
            msg.set_metadata("ontology", self._config.ONTOLOGY)
            msg.set_metadata("language", "JSON")
            msg.body = json.dumps(self.agent.get_chosen_connection())

            try:
                await self.send(msg)
                self._logger.debug("Propose with chosen connection sent!")
            except Exception as e:
                self._logger.error(e)
                self.kill(JobExitCode.FAILURE)
                return

        async def on_end(self):
            self._logger.debug('ProposeChosenConnection ending...')
            self.exit_code = JobExitCode.SUCCESS

    class ReceiveAcceptProposalClientPath(BaseOneShotBehaviour):
        agent: 'ClientAgent'

        def __init__(self, ):
            super().__init__(LOGGER_NAME)

        async def on_start(self):
            self._logger.debug('ReceiveAcceptProposalClientPath running...')

        async def run(self):
            await self.agent.propose_chosen_connection.join()

            msg = await self.receive()
            if msg:
                self._logger.debug(f'Message received with content: {msg.body}')
                body = json.loads(msg.body)
                is_connection_accepted = body['is_connection_accepted']
                self.agent.set_connection_accepted(is_connection_accepted)

            self.kill()

        async def on_end(self):
            self._logger.debug('ReceiveAcceptProposalClientPath ending...')

    async def setup(self):
        self._logger.info('ClientAgent started')
        await self._setup_request_available_connections()
        await self._setup_receive_inform_best_connections()
        await self._setup_receive_availability_for_reservation()

        self.add_behaviour(self.request_available_connections)
        self.add_behaviour(self.receive_inform_best_connections, self.receive_inform_best_connections_template)
        self.add_behaviour(self.receive_availability_for_reservation, self.receive_availability_for_reservation_template)

    def set_best_connections(self, best_connections: List[Connection]):
        self.__best_connections = best_connections

    def set_reservation_available(self, is_reservation_available: bool):
        self.__reservation_available = is_reservation_available

    def set_connection_accepted(self, is_connection_accepted: bool):
        self.__connection_accepted = is_connection_accepted

    def get_chosen_connection(self):
        return self.__chosen_connection

    async def choose_connection(self, connection):
        self.__chosen_connection = connection
        await self._setup_propose_chosen_connection()
        await self._setup_receive_accept_proposal_client_path()

        self.add_behaviour(self.propose_chosen_connection)
        self.add_behaviour(self.receive_accept_proposal_client_path, self.receive_accept_proposal_client_path_template)

    async def _setup_request_available_connections(self):
        self.request_available_connections = self.RequestAvailableConnections()

    async def _setup_receive_inform_best_connections(self):
        self.receive_inform_best_connections_template = BestConnectionsTemplate()
        self.receive_inform_best_connections = self.ReceiveInformBestConnections()

    async def _setup_receive_availability_for_reservation(self):
        self.receive_availability_for_reservation_template = ReservationAvailabilityTemplate()
        self.receive_availability_for_reservation = self.ReceiveAvailabilityForReservation()

    async def _setup_propose_chosen_connection(self):
        self.propose_chosen_connection = self.ProposeChosenConnection()

    async def _setup_receive_accept_proposal_client_path(self):
        self.receive_accept_proposal_client_path_template = AcceptProposalTemplate()
        self.receive_accept_proposal_client_path = self.ReceiveAcceptProposalClientPath()

    def _get_connection_request(self):
        return ConnectionRequest(self.__start_date, self.__origin, self.__destination)


if __name__ == '__main__':
    config = get_config()
    logger = get_logger(LOGGER_NAME)
    driver = ClientAgent(
        config.CLIENT_JID,
        config.CLIENT_PASSWORD,
        start_date=datetime.now(),
        origin='Origin',
        destination='Destination',
    )

    future = driver.start()
    future.result()

    while driver.is_alive():
        try:
            sleep(1)
        except KeyboardInterrupt:
            break

    driver.stop()
    logger.debug('Client agent stopped')
    quit_spade()
