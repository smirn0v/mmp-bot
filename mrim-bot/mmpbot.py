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

class MMPBot(mmpprotocol.MMPCallbackBase):
    def __init__(self,configPath):
        super(MMPBot,self).__init__()
        json_data=open(configPath)
        self.config = json.load(json_data)
        json_data.close()
        self.handlers = { 
                            "say!":     [self.say,"произнести текст"],
                            "allow!":   [self.allow,"разрешить авторизацию пользователя"],
                            "allowed!": [self.allowed,"вывести список людей, которым доступна авторизация"],
                            "about!":   [self.about,"вывести информацию о Johann'е"],
                            "help":     [self.help_command,"вывести это сообщение"]
                        }

    def loginPassword(self):
        return (self.config["email"],self.config["password"])

    def authrizationRequest(self,from_email):
        if from_email in self.config["allowed_emails"]:
            self.protocol.authorize(from_email) 

    def message(self,from_email,message):
        print "%s: %s" % (from_email, message)
        for command in self.handlers:
            if message.startswith(command):
                self.handlers[command][0](from_email,message[len(command)+1:])

    def say(self,from_email,text):
        tempFile = NamedTemporaryFile(delete=False) 
        tempFile.write(text)
        tempFile.close()
        call("cat %s | say" % tempFile.name,shell=True) 
        os.remove(tempFile.name)
        self.protocol.sendMessage(from_email, "сказал")

    def allow(self,from_email,email):
        email = email.strip()
        if not email: return
        self.config["allowed_emails"] += [email]
        self.protocol.sendMessage(from_email, "добавил %s" % email)

    def allowed(self,from_email,args):
        self.protocol.sendMessage(from_email,"%r" % self.config["allowed_emails"])

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
        host, port = mmpprotocol.connection_endpoint()
        reactor.connectTCP(host, port, mmpprotocol.MMPClientFactory(MMPBot(self.configPath)))
        reactor.run()

if __name__ == "__main__":
    daemon = BotDaemon('/tmp/mmp-bot.pid')
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.configPath = os.path.abspath("config.json")
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print "Unknown command"
            sys.exit(2)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)
