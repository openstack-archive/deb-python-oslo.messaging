#    Copyright 2015 Mirantis, Inc.
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

import logging

import six

from oslo_messaging._drivers.zmq_driver.server.consumers \
    import zmq_consumer_base
from oslo_messaging._drivers.zmq_driver.server import zmq_incoming_message
from oslo_messaging._drivers.zmq_driver import zmq_address
from oslo_messaging._drivers.zmq_driver import zmq_async
from oslo_messaging._drivers.zmq_driver import zmq_socket
from oslo_messaging._drivers.zmq_driver import zmq_updater
from oslo_messaging._i18n import _LE

LOG = logging.getLogger(__name__)

zmq = zmq_async.import_zmq()


class SubConsumer(zmq_consumer_base.ConsumerBase):

    def __init__(self, conf, poller, server):
        super(SubConsumer, self).__init__(conf, poller, server)
        self.matchmaker = server.matchmaker
        self.target = server.target
        self.socket = zmq_socket.ZmqSocket(self.conf, self.context, zmq.SUB,
                                           immediate=False)
        self.sockets.append(self.socket)
        self._subscribe_on_target(self.target)
        self.connection_updater = SubscriberConnectionUpdater(
            conf, self.matchmaker, self.socket)
        self.poller.register(self.socket, self.receive_message)

    def _subscribe_on_target(self, target):
        topic_filter = zmq_address.target_to_subscribe_filter(target)
        if target.topic:
            self.socket.setsockopt(zmq.SUBSCRIBE, six.b(target.topic))
        if target.server:
            self.socket.setsockopt(zmq.SUBSCRIBE, six.b(target.server))
        if target.topic and target.server:
            self.socket.setsockopt(zmq.SUBSCRIBE, topic_filter)
        LOG.debug("[%(host)s] Subscribing to topic %(filter)s",
                  {"host": self.socket.handle.identity,
                   "filter": topic_filter})

    @staticmethod
    def _receive_request(socket):
        topic_filter = socket.recv()
        message_id = socket.recv()
        context, message = socket.recv_loaded()
        LOG.debug("Received %(topic_filter)s topic message %(id)s",
                  {'id': message_id, 'topic_filter': topic_filter})
        return context, message

    def receive_message(self, socket):
        try:
            context, message = self._receive_request(socket)
            if not message:
                return None
            return zmq_incoming_message.ZmqIncomingMessage(context, message)
        except (zmq.ZMQError, AssertionError) as e:
            LOG.error(_LE("Receiving message failed: %s"), str(e))

    def cleanup(self):
        self.connection_updater.cleanup()
        super(SubConsumer, self).cleanup()


class SubscriberConnectionUpdater(zmq_updater.ConnectionUpdater):

    def _update_connection(self):
        publishers = self.matchmaker.get_publishers()
        for host, sync in publishers:
            self.socket.connect(zmq_address.get_tcp_direct_address(host))
        LOG.debug("[%s] SUB consumer connected to publishers %s",
                  self.socket.handle.identity, publishers)
