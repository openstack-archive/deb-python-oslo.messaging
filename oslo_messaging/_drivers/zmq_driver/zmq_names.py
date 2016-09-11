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

from oslo_messaging._drivers.zmq_driver import zmq_async

zmq = zmq_async.import_zmq()


FIELD_MSG_ID = 'message_id'
FIELD_REPLY_ID = 'reply_id'
FIELD_REPLY_BODY = 'reply_body'
FIELD_FAILURE = 'failure'


IDX_REPLY_TYPE = 1
IDX_REPLY_BODY = 2

MULTIPART_IDX_ENVELOPE = 0
MULTIPART_IDX_BODY = 1


CALL_TYPE = 1
CAST_TYPE = 2
CAST_FANOUT_TYPE = 3
NOTIFY_TYPE = 4
REPLY_TYPE = 5
ACK_TYPE = 6

MESSAGE_TYPES = (CALL_TYPE,
                 CAST_TYPE,
                 CAST_FANOUT_TYPE,
                 NOTIFY_TYPE)

MULTISEND_TYPES = (CAST_FANOUT_TYPE, NOTIFY_TYPE)
DIRECT_TYPES = (CALL_TYPE, CAST_TYPE, REPLY_TYPE)
CAST_TYPES = (CAST_TYPE, CAST_FANOUT_TYPE)
NOTIFY_TYPES = (NOTIFY_TYPE,)
NON_BLOCKING_TYPES = CAST_TYPES + NOTIFY_TYPES


def socket_type_str(socket_type):
    zmq_socket_str = {zmq.DEALER: "DEALER",
                      zmq.ROUTER: "ROUTER",
                      zmq.PUSH: "PUSH",
                      zmq.PULL: "PULL",
                      zmq.REQ: "REQ",
                      zmq.REP: "REP",
                      zmq.PUB: "PUB",
                      zmq.SUB: "SUB"}
    return zmq_socket_str[socket_type]


def message_type_str(message_type):
    msg_type_str = {CALL_TYPE: "CALL",
                    CAST_TYPE: "CAST",
                    CAST_FANOUT_TYPE: "CAST_FANOUT",
                    NOTIFY_TYPE: "NOTIFY",
                    REPLY_TYPE: "REPLY",
                    ACK_TYPE: "ACK"}
    return msg_type_str[message_type]
