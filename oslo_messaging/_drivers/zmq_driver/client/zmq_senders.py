#    Copyright 2016 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import abc
import logging

import six

from oslo_messaging._drivers.zmq_driver import zmq_async
from oslo_messaging._drivers.zmq_driver import zmq_names

LOG = logging.getLogger(__name__)

zmq = zmq_async.import_zmq()


@six.add_metaclass(abc.ABCMeta)
class SenderBase(object):
    """Base request/ack/reply sending interface."""

    def __init__(self, conf):
        self.conf = conf

    @abc.abstractmethod
    def send(self, socket, message):
        pass


class RequestSender(SenderBase):
    pass


class AckSender(SenderBase):
    pass


class ReplySender(SenderBase):
    pass


class RequestSenderProxy(SenderBase):

    def send(self, socket, request):
        socket.send(b'', zmq.SNDMORE)
        socket.send(six.b(str(request.msg_type)), zmq.SNDMORE)
        socket.send(request.routing_key, zmq.SNDMORE)
        socket.send_string(request.message_id, zmq.SNDMORE)
        socket.send_dumped([request.context, request.message])

        LOG.debug("->[proxy:%(addr)s] Sending %(msg_type)s message "
                  "%(msg_id)s to target %(target)s",
                  {"addr": list(socket.connections),
                   "msg_type": zmq_names.message_type_str(request.msg_type),
                   "msg_id": request.message_id,
                   "target": request.target})


class AckSenderProxy(AckSender):

    def send(self, socket, ack):
        assert ack.msg_type == zmq_names.ACK_TYPE, "Ack expected!"

        socket.send(b'', zmq.SNDMORE)
        socket.send(six.b(str(ack.msg_type)), zmq.SNDMORE)
        socket.send(ack.reply_id, zmq.SNDMORE)
        socket.send_string(ack.message_id)

        LOG.debug("->[proxy:%(addr)s] Sending %(msg_type)s for %(msg_id)s",
                  {"addr": list(socket.connections),
                   "msg_type": zmq_names.message_type_str(ack.msg_type),
                   "msg_id": ack.message_id})


class ReplySenderProxy(SenderBase):

    def send(self, socket, reply):
        assert reply.msg_type == zmq_names.REPLY_TYPE, "Reply expected!"

        socket.send(b'', zmq.SNDMORE)
        socket.send(six.b(str(reply.msg_type)), zmq.SNDMORE)
        socket.send(reply.reply_id, zmq.SNDMORE)
        socket.send_string(reply.message_id, zmq.SNDMORE)
        socket.send_dumped([reply.reply_body, reply.failure])

        LOG.debug("->[proxy:%(addr)s] Sending %(msg_type)s for %(msg_id)s",
                  {"addr": list(socket.connections),
                   "msg_type": zmq_names.message_type_str(reply.msg_type),
                   "msg_id": reply.message_id})


class RequestSenderDirect(SenderBase):

    def send(self, socket, request):
        socket.send(b'', zmq.SNDMORE)
        socket.send(six.b(str(request.msg_type)), zmq.SNDMORE)
        socket.send_string(request.message_id, zmq.SNDMORE)
        socket.send_dumped([request.context, request.message])

        LOG.debug("Sending %(msg_type)s message %(msg_id)s to "
                  "target %(target)s",
                  {"msg_type": zmq_names.message_type_str(request.msg_type),
                   "msg_id": request.message_id,
                   "target": request.target})


class AckSenderDirect(AckSender):

    def send(self, socket, ack):
        assert ack.msg_type == zmq_names.ACK_TYPE, "Ack expected!"

        # not implemented yet

        LOG.debug("Sending %(msg_type)s for %(msg_id)s",
                  {"msg_type": zmq_names.message_type_str(ack.msg_type),
                   "msg_id": ack.message_id})


class ReplySenderDirect(SenderBase):

    def send(self, socket, reply):
        assert reply.msg_type == zmq_names.REPLY_TYPE, "Reply expected!"

        socket.send(reply.reply_id, zmq.SNDMORE)
        socket.send(b'', zmq.SNDMORE)
        socket.send_dumped(reply.to_dict())

        LOG.debug("Sending %(msg_type)s for %(msg_id)s",
                  {"msg_type": zmq_names.message_type_str(reply.msg_type),
                   "msg_id": reply.message_id})
