from mmpbase import *
from twisted.internet import reactor, protocol, task
from twisted.persisted import styles
from twisted.protocols import basic

class MRIMBaseHandler(object):
    def __init__(self, protocol):
        self.auto_remove_handler = True
        self.protocol = protocol

class MRIMLogin2AckHandler(MRIMBaseHandler):
    def __init__(self, protocol, seq):
        super(MRIMLogin2AckHandler,self).__init__(protocol)
        self.seq = seq

    def canHandlePacket(self,packet):
        return packet.header.seq == self.seq and isinstance(packet,MMPServerLoginAckPacket) 

    def handlePacket(self,packet):
        print "Login ack received"

class MRIMLogin2RejHandler(MRIMBaseHandler):
    def __init__(self,protocol,seq):
        super(MRIMLogin2RejHandler,self).__init__(protocol)
        self.seq = seq 

    def canHandlePacket(self,packet):
        return packet.header.seq == self.seq and isinstance(packet,MMPServerLoginRejPacket)

    def handlePacket(self,packet):
        print "[-] Login rejected: %s"%packet.reason

class MRIMHelloAckHandler(MRIMBaseHandler):
    def __init__(self, protocol, seq):
        super(MRIMHelloAckHandler,self).__init__(protocol)
        self.seq = seq
    
    def canHandlePacket(self,packet):
        return packet.header.seq == self.seq and isinstance(packet,MMPServerHelloAckPacket) 

    def handlePacket(self,packet):
        header = self.protocol.createHeader()
        packet = MMPClientLogin2Packet(header,"johann-the-builder@mail.ru","buildpleasemail")
        self.protocol.addHandler(MRIMLogin2RejHandler(self.protocol,header.seq))
        self.protocol.addHandler(MRIMLogin2AckHandler(self.protocol,header.seq))
        self.protocol.sendPacket(packet)

class MRIMDispatcherMixin(object):

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

        print "[+] Packet parsed"        

        packetHandlers = [h for h in self.handlers if h.canHandlePacket(packet)]

        for handler in packetHandlers: 
            handler.handlePacket(packet)
            if handler.auto_remove_handler: 
                self.handlers.remove(handler)

class MRIMMode:
    Header= 1
    Body= 2 

class MRIMProtocol(protocol.Protocol,MRIMDispatcherMixin):
    """
    MRIM protocol implementation
    """

    def __init__(self):
        self.handlers = []
        self.supported_server_packets = [MMPServerHelloAckPacket,
                                         MMPServerLoginAckPacket,
                                         MMPServerLoginRejPacket]
        self.buffer = ""
        self.mode = MRIMMode.Header
        self.seq = 1

    def connectionMade(self):
        print "[+] Connected"
        packet = MMPClientHelloPacket(self.createHeader())
        self.addHandler(MRIMHelloAckHandler(self,packet.header.seq))
        self.sendPacket(packet)
    
    def connectionLost(self,reason):
        pass

    def dataReceived(self,data):
        self.buffer += data
        handlers = { 
                     MRIMMode.Header: self._extractHeader,
                     MRIMMode.Body: self._extractBody
                   }
        handlers[self.mode]()
    
    def createHeader(self):
        header = MMPHeader(seq = self.seq)
        self.seq+=1
        return header

    def sendPacket(self,packet):
       self.transport.write(packet.binary_data())

    def startHeartBeat(self,interval):
        pass

    def _extractHeader(self):
        if len(self.buffer) < MMPHeader.size:
            return
        header_data = self.buffer[:MMPHeader.size]  
        self.buffer = self.buffer[MMPHeader.size:]
        self.header = MMPHeader.from_binary_data(header_data)
        self.mode = MRIMMode.Body
        print "[+] Header received %s"%self.header
        self._extractBody()

    def _extractBody(self):
        if len(self.buffer) < self.header.dlen:
            return
        print "[+] Body received, len = %d"%self.header.dlen
        payload = self.buffer[:self.header.dlen]
        self.buffer = self.buffer[self.header.dlen:]
        self.mode = MRIMMode.Header 
        self.handlePacket(self.header,payload)
        self._extractHeader()

class MRIMClientFactory(protocol.ClientFactory):
    def buildProtocol(self, address):
        return MRIMProtocol()
