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
        self.mode = MRIMMode.Header
        self.seq = 1
        self.supportedPackets = [MMPServerHelloAckPacket]

    def connectionMade(self):
        log.msg("connected")
        packet = MMPClientHelloPacket(self.createHeader())
        self.transport.write(packet.binary_data())
    
    def connectionLost(self):
        pass

    def dataReceived(self,data):
        self.buffer += data
        handlers = { 
                     MRIMMode.Header: extractHeader,
                     MRIMMode.Body: extractBody
                   }
        handlers[self.mode](self)
    
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
        log.msg("header received %s"%header)

    def extractBody(self):
        if len(self.buffer) < self.header.dlen:
            return
