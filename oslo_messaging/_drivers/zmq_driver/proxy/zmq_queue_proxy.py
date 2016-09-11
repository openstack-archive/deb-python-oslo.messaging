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

from oslo_messaging._drivers.zmq_driver.proxy import zmq_publisher_proxy
from oslo_messaging._drivers.zmq_driver import zmq_async
from oslo_messaging._drivers.zmq_driver import zmq_names
from oslo_messaging._drivers.zmq_driver import zmq_socket
from oslo_messaging._drivers.zmq_driver import zmq_updater
from oslo_messaging._i18n import _LI

zmq = zmq_async.import_zmq()
LOG = logging.getLogger(__name__)


class UniversalQueueProxy(object):

    def __init__(self, conf, context, matchmaker):
        self.conf = conf
        self.context = context
        super(UniversalQueueProxy, self).__init__()
        self.matchmaker = matchmaker
        self.poller = zmq_async.get_poller()

        port = conf.zmq_proxy_opts.frontend_port
        host = conf.zmq_proxy_opts.host
        self.fe_router_socket = zmq_socket.ZmqFixedPortSocket(
            conf, context, zmq.ROUTER, host,
            conf.zmq_proxy_opts.frontend_port) if port != 0 else \
            zmq_socket.ZmqRandomPortSocket(conf, context, zmq.ROUTER, host)

        port = conf.zmq_proxy_opts.backend_port
        self.be_router_socket = zmq_socket.ZmqFixedPortSocket(
            conf, context, zmq.ROUTER, host,
            conf.zmq_proxy_opts.backend_port) if port != 0 else \
            zmq_socket.ZmqRandomPortSocket(conf, context, zmq.ROUTER, host)

        self.poller.register(self.fe_router_socket.handle,
                             self._receive_in_request)
        self.poller.register(self.be_router_socket.handle,
                             self._receive_in_request)

        self.pub_publisher = zmq_publisher_proxy.PublisherProxy(
            conf, matchmaker)

        self._router_updater = RouterUpdater(
            conf, matchmaker, self.pub_publisher.host,
            self.fe_router_socket.connect_address,
            self.be_router_socket.connect_address)

    def run(self):
        message, socket = self.poller.poll()
        if message is None:
            return

        msg_type = message[0]
        if self.conf.oslo_messaging_zmq.use_pub_sub and \
                msg_type in (zmq_names.CAST_FANOUT_TYPE,
                             zmq_names.NOTIFY_TYPE):
            self.pub_publisher.send_request(message)
        else:
            self._redirect_message(self.be_router_socket.handle
                                   if socket is self.fe_router_socket.handle
                                   else self.fe_router_socket.handle, message)

    @staticmethod
    def _receive_in_request(socket):
        try:
            reply_id = socket.recv()
            assert reply_id is not None, "Valid id expected"
            empty = socket.recv()
            assert empty == b'', "Empty delimiter expected"
            msg_type = int(socket.recv())
            routing_key = socket.recv()
            payload = socket.recv_multipart()
            payload.insert(0, reply_id)
            payload.insert(0, routing_key)
            payload.insert(0, msg_type)
            return payload
        except (AssertionError, ValueError, zmq.ZMQError):
            LOG.error("Received message with wrong format")
            return None

    @staticmethod
    def _redirect_message(socket, multipart_message):
        message_type = multipart_message.pop(0)
        routing_key = multipart_message.pop(0)
        reply_id = multipart_message.pop(0)
        message_id = multipart_message[0]
        socket.send(routing_key, zmq.SNDMORE)
        socket.send(b'', zmq.SNDMORE)
        socket.send(reply_id, zmq.SNDMORE)
        socket.send(six.b(str(message_type)), zmq.SNDMORE)
        LOG.debug("Dispatching %(msg_type)s message %(msg_id)s - from %(rid)s "
                  "to -> %(rkey)s" %
                  {"msg_type": zmq_names.message_type_str(message_type),
                   "msg_id": message_id,
                   "rkey": routing_key,
                   "rid": reply_id})
        socket.send_multipart(multipart_message)

    def cleanup(self):
        self.fe_router_socket.close()
        self.be_router_socket.close()
        self.pub_publisher.cleanup()
        self._router_updater.cleanup()


class RouterUpdater(zmq_updater.UpdaterBase):
    """This entity performs periodic async updates
    from router proxy to the matchmaker.
    """

    def __init__(self, conf, matchmaker, publisher_address, fe_router_address,
                 be_router_address):
        self.publisher_address = publisher_address
        self.fe_router_address = fe_router_address
        self.be_router_address = be_router_address
        super(RouterUpdater, self).__init__(conf, matchmaker,
                                            self._update_records)

    def _update_records(self):
        self.matchmaker.register_publisher(
            (self.publisher_address, self.fe_router_address),
            expire=self.conf.oslo_messaging_zmq.zmq_target_expire)
        LOG.info(_LI("[PUB:%(pub)s, ROUTER:%(router)s] Update PUB publisher"),
                 {"pub": self.publisher_address,
                  "router": self.fe_router_address})
        self.matchmaker.register_router(
            self.be_router_address,
            expire=self.conf.oslo_messaging_zmq.zmq_target_expire)
        LOG.info(_LI("[Backend ROUTER:%(router)s] Update ROUTER"),
                 {"router": self.be_router_address})

    def cleanup(self):
        super(RouterUpdater, self).cleanup()
        self.matchmaker.unregister_publisher(
            (self.publisher_address, self.fe_router_address))
        self.matchmaker.unregister_router(
            self.be_router_address)
