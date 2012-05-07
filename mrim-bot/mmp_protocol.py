from mmpbase import *
from twisted.internet import reactor, protocol, task
from twisted.persisted import styles
from twisted.protocols import basic

class MMPBaseHandler(object):
    def __init__(self, protocol):
        self.auto_remove_handler = True
        self.protocol = protocol

class MMPLogin2AckHandler(MMPBaseHandler):
    def __init__(self, protocol, seq):
        super(MMPLogin2AckHandler,self).__init__(protocol)
        self.seq = seq

    def canHandlePacket(self,packet):
        return packet.header.seq == self.seq and isinstance(packet,MMPServerLoginAckPacket) 

    def handlePacket(self,packet):
        print "[+] Logged in"

class MMPLogin2RejHandler(MMPBaseHandler):
    def __init__(self,protocol,seq):
        super(MMPLogin2RejHandler,self).__init__(protocol)
        self.seq = seq 

    def canHandlePacket(self,packet):
        return packet.header.seq == self.seq and isinstance(packet,MMPServerLoginRejPacket)

    def handlePacket(self,packet):
        print "[-] Login rejected: %s"%packet.reason

class MMPHelloAckHandler(MMPBaseHandler):
    def __init__(self, protocol, seq):
        super(MMPHelloAckHandler,self).__init__(protocol)
        self.seq = seq
    
    def canHandlePacket(self,packet):
        return packet.header.seq == self.seq and isinstance(packet,MMPServerHelloAckPacket) 

    def handlePacket(self,packet):
        self.protocol.startHeartbeat(packet.interval)
        header = self.protocol.createHeader()
        packet = MMPClientLogin2Packet(header,"johann-the-builder@mail.ru","buildpleasemail")
        self.protocol.addHandler(MMPLogin2RejHandler(self.protocol,header.seq))
        self.protocol.addHandler(MMPLogin2AckHandler(self.protocol,header.seq))
        self.protocol.sendPacket(packet)

class MMPMessageAckHandler(MMPBaseHandler):
    def __init__(self,protocol):
        super(MMPMessageAckHandler,self).__init__(protocol)
        self.auto_remove_handler = False
    
    def canHandlePacket(self,packet):
        return isinstance(packet,MMPServerMessageAckPacket)

    def handlePacket(self,packet):
        header = self.protocol.createHeader()
        header.seq = packet.header.seq
        msgReceivedPacket = MMPClientMessageRecv(header,packet.from_email,packet.msgid)
        self.protocol.sendPacket(msgReceivedPacket)

class MMPIncomingAuthorizationHandler(MMPBaseHandler):
    def __init__(self,protocol):
        super(MMPMessageAckHandler,self).__init__(protocol)
        self.auto_remove_handler = False

    def canHandlePacket(self,packet):
        return packet.header.seq == self.seq and \
               isinstance(packet,MMPServerMessageAckPacket) and \
               packet.flag_set(MESSAGE_FLAG_AUTHORIZE)

    def handlePacket(self,packet):
        print "[+] Authorization request received from %s"%packet.from_email 

class MMPDispatcherMixin(object):

    def addHandler(self,handler):
        self.handlers += [handler]

    def formPacket(self,header,payload):
        for packet_class in self.supported_server_packets:
            if packet_class.msg == header.msg:
                return packet_class(header,payload) 
        return None 

    def handlePacket(self,header,payload):
        packet = self.formPacket(header,payload)

        if not packet: return

        packetHandlers = [h for h in self.handlers if h.canHandlePacket(packet)]

        for handler in packetHandlers: 
            handler.handlePacket(packet)
            if handler.auto_remove_handler: 
                self.handlers.remove(handler)

class MMPMode:
    Header= 1
    Body= 2 

class MMPProtocol(protocol.Protocol,MMPDispatcherMixin):
    """
    MMP protocol implementation
    """

    def __init__(self):
        self.handlers = []
        self.supported_server_packets = [MMPServerHelloAckPacket,
                                         MMPServerLoginAckPacket,
                                         MMPServerLoginRejPacket,
                                         MMPServerMessageAckPacket,
                                         MMPServerContactListPacket]
        self.buffer = ""
        self.mode = MMPMode.Header
        self.seq = 1
            
        self.addHandler(MMPMessageAckHandler(self))

    def connectionMade(self):
        print "[+] Connected"
        packet = MMPClientHelloPacket(self.createHeader())
        self.addHandler(MMPHelloAckHandler(self,packet.header.seq))
        self.sendPacket(packet)
    
    def connectionLost(self,reason):
        pass

    def dataReceived(self,data):
        self.buffer += data
        handlers = { 
                     MMPMode.Header: self._extractHeader,
                     MMPMode.Body: self._extractBody
                   }
        handlers[self.mode]()
    
    def createHeader(self):
        header = MMPHeader(seq = self.seq)
        self.seq+=1
        return header

    def sendPacket(self,packet):
       self.transport.write(packet.binary_data())

    def startHeartbeat(self,interval):
        heartbeat = task.LoopingCall(self._sendHeartbeat)
        heartbeat.start(interval, now = False)

    def _sendHeartbeat(self):
        header = self.createHeader()
        packet = MMPClientPingPacket(header)
        self.sendPacket(packet)

    def _extractHeader(self):
        if len(self.buffer) < MMPHeader.size:
            return
        header_data = self.buffer[:MMPHeader.size]  
        self.buffer = self.buffer[MMPHeader.size:]
        self.header = MMPHeader.from_binary_data(header_data)
        self.mode = MMPMode.Body
        print "[+] Header received %s"%self.header
        self._extractBody()

    def _extractBody(self):
        if len(self.buffer) < self.header.dlen:
            return
        print "[+] Body received, len = %d"%self.header.dlen
        payload = self.buffer[:self.header.dlen]
        self.buffer = self.buffer[self.header.dlen:]
        self.mode = MMPMode.Header 

        print "[+] Payload: %s"%payload.encode('hex')

        self.handlePacket(self.header,payload)
        self._extractHeader()

class MMPClientFactory(protocol.ClientFactory):
    def buildProtocol(self, address):
        return MMPProtocol()
