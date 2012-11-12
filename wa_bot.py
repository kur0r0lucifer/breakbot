#!/usr/bin/python
# Copyright 2012 Bruno Gonzalez
# This software is released under the GNU AFFERO GENERAL PUBLIC LICENSE (see agpl-3.0.txt or www.gnu.org/licenses/agpl-3.0.html)
import threading
from message import Message
from timestamp import Timestamp

from Yowsup.Tools.utilities import Utilities
from Yowsup.connectionmanager import YowsupConnectionManager
import time

class WAInterface(threading.Thread):
    def __init__(self, username, identity, msg_handler, stopped_handler):
        threading.Thread.__init__(self)
        self.connected = False
        self.must_run = False
        self.msg_handler = msg_handler
        self.stopped_handler = stopped_handler
        self.username = username
        self.identity = identity
    def wait_connected(self):
        while not self.connected:
            if not self.must_run:
                raise Exception("Interrupting because it must not run")
            time.sleep(0.1)
    def onMessageReceived(self, messageId, jid, messageContent, timestamp, wantsReceipt):
        try:
            print "simple messageId %s, jid %s, content %s" %(messageId, jid, messageContent)
            message = Message("wa", jid, self.username, messageContent)
            message.time = Timestamp(ms_int = timestamp*1000)
            self.msg_handler(message)
            sendReceipts = True
            if wantsReceipt and sendReceipts:
                self.wait_connected()
                self.methodsInterface.call("message_ack", (jid, messageId))
        except Exception,e:
            print "Error while handling message: %s" %e
    def onGroup_MessageReceived(self, messageId, jid, author, messageContent, timestamp, wantsReceipt):
        try:
            print "group messageId %s, jid %s, author %s, content %s" %(messageId, jid, author, messageContent)
            message = Message("wa", author, jid, messageContent)
            message.time = Timestamp(ms_int = timestamp*1000)
            self.msg_handler(message)
            sendReceipts = True
            if wantsReceipt and sendReceipts:
                self.wait_connected()
                self.methodsInterface.call("message_ack", (jid, messageId))
        except Exception,e:
            print "Error while handling message: %s" %e

    def run(self):
        try:
            print "WA: connecting as %s" %self.username
            self.must_run = True
            self.cm = YowsupConnectionManager()
            self.cm.setAutoPong(True)
            self.signalsInterface = self.cm.getSignalsInterface()
            self.methodsInterface = self.cm.getMethodsInterface()
            self.signalsInterface.registerListener("message_received", self.onMessageReceived)
            self.signalsInterface.registerListener("group_messageReceived", self.onGroup_MessageReceived)
            self.signalsInterface.registerListener("auth_success", self.onAuthSuccess)
            self.signalsInterface.registerListener("auth_fail", self.onAuthFailed)
            self.signalsInterface.registerListener("disconnected", self.onDisconnected)
            self.signalsInterface.registerListener("receipt_messageSent", self.onMessageSent)
            self.signalsInterface.registerListener("receipt_messageDelivered", self.onMessageDelivered)
            self.signalsInterface.registerListener("ping", self.onPing)

            self.methodsInterface.call("auth_login", (self.username, Utilities.getPassword(self.identity)))
            self.wait_connected()
            print "WA: connected as %s" %self.username
            while self.must_run:
                time.sleep(0.5)
                #raw_input()
        except Exception, e:
            print "Error in WA loop: %s" %e
        print "WA: disconnected"
        self.connected = False
        self.stopped_handler()
    def stop(self):
        self.must_run = False
    def send(self, target, text):
        self.wait_connected()
        self.methodsInterface.call("message_send", (target, text))
        print " >>> Sent WA message: %s: %s" %(target, text)
    def onAuthSuccess(self, username):
        print "Authed %s" % username
        self.connected = True
        self.methodsInterface.call("ready")
    def onAuthFailed(self, username, err):
        print "Auth Failed!"
    def onDisconnected(self, reason):
        print "Disconnected because %s" %reason
    def onMessageSent(self, jid, messageId):
        print "Message was sent successfully to %s" % jid
    def onMessageDelivered(self, jid, messageId):
        print "Message was delivered successfully to %s" %jid
        self.wait_connected()
        self.methodsInterface.call("delivered_ack", (jid, messageId))
    def onPing(self, pingId):
        print "ponging to %s" %pingId
        self.wait_connected()
        self.methodsInterface.call("pong", (pingId,))


