from mmpbase import *
from twisted.internet import reactor, protocol, task
from twisted.persisted import styles
from twisted.protocols import basic

class MRIMHelloAckHandler(object):
    pass

class MRIMDispatcherMixin(object):
    pass
    
class MRIMMode:
    Header= 1
    Body= 2 

class MRIMProtocol(protocol.Protocol,MRIMDispatcherMixin):
    """
    MRIM protocol implementation
    """

    def __init__(self):
        self.buffer = ""
        self.mode = MRIMMode.Header
        self.seq = 1
        self.supportedPackets = [MMPServerHelloAckPacket]

    def connectionMade(self):
        print "[+] Connected"
        packet = MMPClientHelloPacket(self.createHeader())
        self.transport.write(packet.binary_data())
    
    def connectionLost(self,reason):
        pass

    def dataReceived(self,data):
        self.buffer += data
        handlers = { 
                     MRIMMode.Header: self.extractHeader,
                     MRIMMode.Body: self.extractBody
                   }
        handlers[self.mode]()
    
    def createHeader(self):
        header = MMPHeader(seq = self.seq)
        self.seq+=1
        return header

    def extractHeader(self):
        if len(self.buffer) < MMPHeader.size:
            return
        header_data = self.buffer[:MMPHeader.size]  
        self.buffer = self.buffer[MMPHeader.size:]
        self.header = MMPHeader.from_binary_data(header_data)
        self.mode = MRIMMode.Body
        print "[+] Header received %s"%self.header
        self.extractBody()

    def extractBody(self):
        if len(self.buffer) < self.header.dlen:
            return
        print "[+] Body received, len = %d"%self.header.dlen
        self.buffer = self.buffer[self.header.dlen:]
        self.mode = MRIMMode.Header 
        self.extractHeader()

class MRIMClientFactory(protocol.ClientFactory):
    def buildProtocol(self, address):
        return MRIMProtocol()
