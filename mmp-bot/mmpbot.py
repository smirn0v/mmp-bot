#!/usr/bin/python
# -*- coding: utf8 -*-

import mmpprotocol
import json
import sys
import os
from twisted.internet import reactor
from daemon import Daemon
from subprocess import call
from tempfile import NamedTemporaryFile

def startbot(configpath):
    host, port = mmpprotocol.connection_endpoint()
    reactor.connectTCP(host, port, mmpprotocol.MMPClientFactory(MMPBot(configpath)))
    reactor.run()

class MMPBot(mmpprotocol.MMPCallbackBase):
    def __init__(self,configPath):
        super(MMPBot,self).__init__()
        json_data=open(configPath)
        self.config = json.load(json_data)
        json_data.close()
        self.handlers = { 
                            "about":   [self.about,"вывести информацию о Johann'е"],
                            "help":     [self.help_command,"вывести это сообщение"]
                        }

    def loginPassword(self):
        return (self.config["email"],self.config["password"])

    def authrizationRequest(self,from_email):
        self.protocol.authorize(from_email) 

    def message(self,from_email,message):
        print "%s: %s" % (from_email, message)
        self.protocol.sendMessage(from_email,"pong")
        for command in self.handlers:
            if message.startswith(command):
                self.handlers[command][0](from_email,message[len(command)+1:])

    def about(self,from_email,args):
        self.protocol.sendMessage(from_email,"Johann - Mail.Ru build bot by Alexander Smirnov (alexander@smirn0v.ru)")

    def help_command(self,from_email,args):
        reply = "Поддерживаемые команды: \n"
        reply += "\n".join([k+" - %s"%v[1] for k,v in self.handlers.iteritems()])
        self.protocol.sendMessage(from_email,reply)

class BotDaemon(Daemon):
    def __init__(self,pidfile):
        super(BotDaemon,self).__init__(pidfile,stdout='/tmp/mmp-bot-out.log',stderr='/tmp/mmp-bot.log')
        self.configPath = None
    def run(self):
        startbot(self.configpath)

if __name__ == "__main__":
    daemon = BotDaemon('/tmp/mmp-bot.pid')
    configpath = os.path.abspath("config.json")
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.configPath = configpath
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        elif 'no-daemon' == sys.argv[1]:
            startbot(configpath)
        else:
            print "Unknown command"
            sys.exit(2)
    else:
        print "usage: %s start|stop|restart|no-daemon" % sys.argv[0]
        sys.exit(2)
