#
# do_celu
#
# Copyright 2022 Agenty 007
#

from time import sleep
from logging import Logger
from spade import agent, quit_spade
from spade.message import Message
from do_celu.utils.performatives import Performatives
from do_celu.behaviours import BaseOneShotBehaviour
from do_celu.config import Config, get_config
from do_celu.context import get_logger
from do_celu.utils.job_exit_code import JobExitCode
from do_celu.messages.manager import ReceiveAvailableDriversRequestTemplate

LOGGER_NAME = get_config().MANAGER_LOGGER_NAME


class ManagerAgent(agent.Agent):
    # Behaviours:
    receive_welcome_driver_msg: 'ReceiveWelcomeDriverMsg'
    receive_available_drivers_request: 'ReceiveAvailableDriversRequest'
    receive_available_drivers_request_template: 'ReceiveAvailableDriversRequestTemplate'
    request_driver_data: 'RequestDriverData'
    receive_driver_data: 'ReceiveDriverData'
    request_best_paths: 'RequestBestPaths'
    receive_best_paths: 'ReceiveBestPaths'
    inform_client_best_paths: 'InformClientBestPaths'
    cfp_client_choose_path: 'CFPClientChoosePath'
    receive_client_path_proposal: 'ReceiveClientPathProposal'
    inform_driver_path_change: 'InformDriverPathChange'
    accept_client_path_proposal: 'AcceptClientPathProposal'

    # Agent state:
    _logger: Logger
    _config: Config

    def __init__(self, jid: str, password: str, verify_security: bool = False):
        super().__init__(jid, password, verify_security=verify_security)
        self._config = get_config()
        self._logger = get_logger(LOGGER_NAME)

    class ReceiveWelcomeDriverMsg(BaseOneShotBehaviour):
        agent: 'ManagerAgent'

        def __init__(self,):
            super().__init__(LOGGER_NAME)

        async def on_start(self):
            self._logger.debug('ReceiveWelcomeDriverMsg running...')

        def on_available(self, jid, stanza):
            self._logger.debug("[{}] Agent {} is available.".format(self.agent.name, jid.split("@")[0]))

        def on_subscribed(self, jid):
            self._logger.debug("[{}] Agent {} has accepted the subscription.".format(self.agent.name, jid.split("@")[0]))
            self._logger.debug("[{}] Contacts List: {}".format(self.agent.name, self.agent.presence.get_contacts()))

        def on_subscribe(self, jid):
            self._logger.debug("[{}] Agent {} asked for subscription. Let's aprove it.".format(self.agent.name, jid.split("@")[0]))
            self.presence.approve(jid)
            self.presence.subscribe(jid)

        async def run(self):
            self._logger.info(f'test {self.presence.get_contacts()}')  # TODO remove
            self.presence.on_subscribe = self.on_subscribe
            self.presence.on_subscribed = self.on_subscribed
            self.presence.on_available = self.on_available
            self.presence.set_available()

    class ReceiveAvailableDriversRequest(BaseOneShotBehaviour):
        agent: 'ManagerAgent'

        def __init__(self,):
            super().__init__(LOGGER_NAME)

        async def on_start(self):
            self._logger.debug('ReceiveAvailableDriversRequest running...')

        async def run(self):
            msg = await self.receive(timeout=30)
            if msg:
                self._logger.debug(f'ReceiveAvailableDriversRequest msg received with body: {msg.body}')
                if not self.agent.has_behaviour(self.agent.request_driver_data):
                    self._logger.debug('RequestDriverData renewed')
                    await self.agent._setup_receive_available_drivers_request()
                    self.agent.add_behaviour(self.agent.request_driver_data)
                self.exit_code = JobExitCode.SUCCESS
            else:
                self.exit_code = JobExitCode.FAILURE

        async def on_end(self):
            self._logger.debug(f'ReceiveAvailableDriversRequest ended with status: {self.exit_code.name}')

    class RequestDriverData(BaseOneShotBehaviour):
        agent: 'ManagerAgent'

        def __init__(self,):
            super().__init__(LOGGER_NAME)

        async def on_start(self):
            self._logger.debug('RequestDriverData running...')

        async def run(self):
            for contact in self.presence.get_contacts():
                if 'driver' in str(contact):
                    msg = Message(to=contact)
                    msg.set_metadata('performative', Performatives.REQUEST)
                    # msg.body = #TODO
                    await self.send(msg)
            self.exit_code = JobExitCode.SUCCESS

        async def on_end(self):
            self._logger.debug(f'RequestDriverData ended with status: {self.exit_code.name}')

    class ReceiveDriverData(BaseOneShotBehaviour):
        agent: 'ManagerAgent'

        def __init__(self,):
            super().__init__(LOGGER_NAME)

        async def on_start(self):
            self._logger.debug('ReceiveDriverData running...')

        async def run(self):
            msg = await self.receive(timeout=30)
            if msg:
                self._logger.debug(f'ReceiveDriverData msg received with body: {msg.body}')
                # TODO trigger getting best paths (maybe after x seconds after first respond)
                # - prob move to other behavior
                self.exit_code = JobExitCode.SUCCESS
            else:
                self.exit_code = JobExitCode.FAILURE

        async def on_end(self):
            self._logger.debug(f'ReceiveDriverData ended with status: {self.exit_code.name}')

    class RequestBestPaths(BaseOneShotBehaviour):
        agent: 'ManagerAgent'

        def __init__(self,):
            super().__init__(LOGGER_NAME)

        async def on_start(self):
            self._logger.debug('RequestBestPaths running...')

        async def run(self):
            msg = Message(to=self._config.MATHEMATICIAN_JID)
            msg.set_metadata('performative', Performatives.REQUEST)
            # msg.body = #TODO
            await self.send(msg)
            self.exit_code = JobExitCode.SUCCESS

        async def on_end(self):
            self._logger.debug(f'RequestBestPaths ended with status: {self.exit_code.name}')

    class ReceiveBestPaths(BaseOneShotBehaviour):
        agent: 'ManagerAgent'

        def __init__(self,):
            super().__init__(LOGGER_NAME)

        async def on_start(self):
            self._logger.debug('ReceiveBestPaths running...')

        async def run(self):
            msg = await self.receive(timeout=30)
            if msg:
                self._logger.debug(f'ReceiveBestPaths msg received with body: {msg.body}')
                # TODO send to client
                self.exit_code = JobExitCode.SUCCESS
            else:
                self.exit_code = JobExitCode.FAILURE

        async def on_end(self):
            self._logger.debug(f'ReceiveBestPaths ended with status: {self.exit_code.name}')

    class InformClientBestPaths(BaseOneShotBehaviour):
        agent: 'ManagerAgent'

        def __init__(self,):
            super().__init__(LOGGER_NAME)

        async def on_start(self):
            self._logger.debug('InformClientBestPaths running...')

        async def run(self):
            msg = Message(to='client@localhost')  # TODO select good client
            msg.set_metadata('performative', Performatives.INFORM)
            # msg.body = #TODO
            await self.send(msg)
            self.exit_code = JobExitCode.SUCCESS

        async def on_end(self):
            self._logger.debug(f'InformClientBestPaths ended with status: {self.exit_code.name}')

    class CFPClientChoosePath(BaseOneShotBehaviour):
        agent: 'ManagerAgent'

        def __init__(self,):
            super().__init__(LOGGER_NAME)

        async def on_start(self):
            self._logger.debug('CFPClientChoosePath running...')

        async def run(self):
            msg = Message(to='client@localhost')  # TODO select good client
            msg.set_metadata('performative', Performatives.CALL_FOR_PROPOSAL)
            # msg.body = #TODO
            await self.send(msg)
            self.exit_code = JobExitCode.SUCCESS

        async def on_end(self):
            self._logger.debug(f'CFPClientChoosePath ended with status: {self.exit_code.name}')

    class ReceiveClientPathProposal(BaseOneShotBehaviour):
        agent: 'ManagerAgent'

        def __init__(self,):
            super().__init__(LOGGER_NAME)

        async def on_start(self):
            self._logger.debug('ReceiveClientPathProposal running...')

        async def run(self):
            msg = await self.receive(timeout=30)
            if msg:
                self._logger.debug(f'ReceiveClientPathProposal msg received with body: {msg.body}')
                # TODO send info to driver
                # TODO after that accept proposal
                self.exit_code = JobExitCode.SUCCESS
            else:
                self.exit_code = JobExitCode.FAILURE

        async def on_end(self):
            self._logger.debug(f'ReceiveClientPathProposal ended with status: {self.exit_code.name}')

    class InformDriverPathChange(BaseOneShotBehaviour):
        agent: 'ManagerAgent'

        def __init__(self,):
            super().__init__(LOGGER_NAME)

        async def on_start(self):
            self._logger.debug('InformDriverPathChange running...')

        async def run(self):
            msg = Message(to='driver@localhost')  # TODO select good driver
            msg.set_metadata('performative', Performatives.INFORM)
            # msg.body = #TODO
            await self.send(msg)
            self.exit_code = JobExitCode.SUCCESS

        async def on_end(self):
            self._logger.debug(f'InformDriverPathChange ended with status: {self.exit_code.name}')

    class AcceptClientPathProposal(BaseOneShotBehaviour):
        agent: 'ManagerAgent'

        def __init__(self,):
            super().__init__(LOGGER_NAME)

        async def on_start(self):
            self._logger.debug('AcceptClientPathProposal running...')

        async def run(self):
            msg = Message(to='client@localhost')  # TODO select good client
            msg.set_metadata('performative', Performatives.ACCEPT_PROPOSAL)
            # msg.body = #TODO
            await self.send(msg)
            self.exit_code = JobExitCode.SUCCESS

        async def on_end(self):
            self._logger.debug(f'AcceptClientPathProposal ended with status: {self.exit_code.name}')

    async def setup(self):
        self._logger.info('ManagerAgent started')


        # TODO temp remove
        self.add_behaviour(self.RequestDriverData())
        # self.add_behaviour(self.ReceiveAvailableDriversRequest()) # TODO fix client
        self.add_behaviour(self.ReceiveWelcomeDriverMsg())
        # self.add_behaviour(self.ReceiveDriverData())
        # self.add_behaviour(self.RequestBestPaths())
        # self.add_behaviour(self.ReceiveBestPaths())
        # self.add_behaviour(self.InformClientBestPaths())
        # self.add_behaviour(self.CFPClientChoosePath())
        # self.add_behaviour(self.ReceiveClientPathProposal())
        # self.add_behaviour(self.InformDriverPathChange())
        # self.add_behaviour(self.AcceptClientPathProposal())

    async def _setup_receive_available_drivers_request(self):
        self.receive_available_drivers_request_template = ReceiveAvailableDriversRequestTemplate()
        self.receive_available_drivers_request = self.ReceiveAvailableDriversRequest()


if __name__ == '__main__':
    config = get_config()
    logger = get_logger(config.MANAGER_LOGGER_NAME)
    manager = ManagerAgent(
        config.MANAGER_JID,
        config.MANAGER_PASSWORD,
    )

    future = manager.start()
    future.result()

    while manager.is_alive():
        try:
            sleep(1)
        except KeyboardInterrupt:
            break

    manager.stop()
    logger.debug('Manager agent stopped')
    quit_spade()
