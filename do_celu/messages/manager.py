#
# do_celu
#
# Copyright 2022 Agenty 007
#
from spade.message import Message
from spade.template import Template

from do_celu.utils.performatives import Performatives
from do_celu.messages.base_message import BaseMessage


class _ReceiveAvailableDriversRequestMessageBase(BaseMessage):

    def _set_custom_properties(self) -> None:
        self.set_metadata("performative", Performatives.REQUEST.value)
        self.set_metadata("ontology", self._config.ONTOLOGY)
        self.set_metadata("language", "JSON")
        self.set_metadata('behaviour', 'request_available_drivers')


class ReceiveAvailableDriversRequestTemplate(_ReceiveAvailableDriversRequestMessageBase, Template):
    pass


class ReceiveAvailableDriversRequestMessage(_ReceiveAvailableDriversRequestMessageBase, Message):
    pass

