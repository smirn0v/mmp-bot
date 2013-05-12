from mmpbase import *
from twisted.internet import reactor, protocol, task
from twisted.persisted import styles
from twisted.protocols import basic
import telnetlib

__metaclass__ = type

class MMPInvalidEndpoint(Exception):
    pass

def connection_endpoint():
    telnet = telnetlib.Telnet("mrim.mail.ru",2042)
    address = telnet.read_all()
    telnet.close()

    host,port = address.split(":")

    if host == None or port == None or \
       len(port) < 2 or port[-1] != '\n': 
        raise MMPInvalidEndpoint, "Invalid mrim server response"

    port = port[:-1] #trim '\n'
    if not port.isdigit(): raise MMPInvalidEndpoint, "Invalid mrim server response"

    return host,int(port) 

class MMPCallbackBase:
    def __init__(self):
        self.protocol = None
    def loginPassword(self):
        """ 
        return tuple ("email","password")
        that should be used during login process
        """
    def loggedIn(self):
        """
        called on successfull login
        """
    def faildedToLogin(self,reason):
        """
        called in case of login was failed
        """
    def message(self,from_email,message):
        """
        called if message received
        """
    def authorizationRequest(self,from_email):
        """
        called if authorization request was received
        """

class MMPBaseHandler:
    def __init__(self, protocol):
        self.auto_remove_handler = True
        self.protocol = protocol

class MMPLogin2AckHandler(MMPBaseHandler):
    def __init__(self, protocol, seq):
        super(MMPLogin2AckHandler,self).__init__(protocol)
        self.packet_class = MMPServerLoginAckPacket
        self.seq = seq

    def canHandlePacket(self,packet):
        return packet.header.seq == self.seq and isinstance(packet,self.packet_class) 

    def handlePacket(self,packet):
        self.protocol.callback.loggedIn()

class MMPLogin2RejHandler(MMPBaseHandler):
    def __init__(self,protocol,seq):
        super(MMPLogin2RejHandler,self).__init__(protocol)
        self.packet_class = MMPServerLoginRejPacket
        self.seq = seq 

    def canHandlePacket(self,packet):
        return packet.header.seq == self.seq and isinstance(packet,self.packet_class)

    def handlePacket(self,packet):
        self.protocol.callback.failedToLogin(packet.reason)

class MMPHelloAckHandler(MMPBaseHandler):
    def __init__(self, protocol, seq):
        super(MMPHelloAckHandler,self).__init__(protocol)
        self.packet_class = MMPServerHelloAckPacket
        self.seq = seq
    
    def canHandlePacket(self,packet):
        return packet.header.seq == self.seq and isinstance(packet,self.packet_class) 

    def handlePacket(self,packet):
        self.protocol.startHeartbeat(packet.interval)
        header = self.protocol.createHeader()
        loginPassword = self.protocol.callback.loginPassword()
        packet = MMPClientLogin2Packet(header,loginPassword[0].encode('ascii'),loginPassword[1].encode('ascii'))

        self.protocol.addHandler(MMPLogin2RejHandler(self.protocol,header.seq))
        self.protocol.addHandler(MMPLogin2AckHandler(self.protocol,header.seq))

        self.protocol.sendPacket(packet)

class MMPMessageAckHandler(MMPBaseHandler):
    def __init__(self,protocol):
        super(MMPMessageAckHandler,self).__init__(protocol)
        self.packet_class = MMPServerMessageAckPacket
        self.auto_remove_handler = False
    
    def canHandlePacket(self,packet):
        return isinstance(packet,self.packet_class)

    def handlePacket(self,packet):
        print "message: %s, flags 0x%X"%(packet.message,packet.flags)
       
        if packet.simple_message():   
            self.protocol.callback.message(packet.from_email,packet.message)

        if packet.flag_set(MESSAGE_FLAG_AUTHORIZE):
            print "sending auth ok"
            self.protocol.authorize(packet.from_email)

        if packet.flag_set(MESSAGE_FLAG_NORECV):
            return

        header = self.protocol.createHeader()
        header.seq = packet.header.seq
        msgReceivedPacket = MMPClientMessageRecvPacket(header,packet.from_email,packet.msgid)
        self.protocol.sendPacket(msgReceivedPacket)

class MMPIncomingAuthorizationHandler(MMPBaseHandler):
    def __init__(self,protocol):
        super(MMPIncomingAuthorizationHandler,self).__init__(protocol)
        self.packet_class = MMPServerMessageAckPacket
        self.auto_remove_handler = False

    def canHandlePacket(self,packet):
        return isinstance(packet,self.packet_class) and \
               packet.flag_set(MESSAGE_FLAG_AUTHORIZE)

    def handlePacket(self,packet):
        self.protocol.callback.authrizationRequest(packet.from_email)

class MMPDispatcherMixin:

    def addHandler(self,handler):
        self.handlers += [handler]

    def formPacket(self,header,payload):
        packet_classes = [h.packet_class for h in self.handlers]
        for packet_class in packet_classes:
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

    def __init__(self,callback):
        callback.protocol = self
        self.callback = callback
        self.heartbeat = None
        self.handlers = []
        self.buffer = ""
        self.mode = MMPMode.Header
        self.seq = 1
            
        self.addHandler(MMPMessageAckHandler(self))
        self.addHandler(MMPIncomingAuthorizationHandler(self))

    def connectionMade(self):
        packet = MMPClientHelloPacket(self.createHeader())
        self.addHandler(MMPHelloAckHandler(self,packet.header.seq))
        self.sendPacket(packet)
    
    def connectionLost(self,reason):
        self.stopHeartbeat()

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

    def sendMessage(self,to_email,message):
        """ 
        message expected to be in ascii
        rtf not supported
        """
        header = self.createHeader()
        packet = MMPClientMessagePacket(header,flags=0,to_email=to_email,message=message.decode('utf8').encode('cp1251'))
        self.sendPacket(packet)

    def authorize(self,email):
        header = self.createHeader()
        authorizePacket = MMPClientAuthorizePacket(header,email)
        self.sendPacket(authorizePacket)

    def startHeartbeat(self,interval):
        self.stopHeartbeat()
        self.heartbeat = task.LoopingCall(self._sendHeartbeat)
        self.heartbeat.start(interval, now = False)

    def stopHeartbeat(self):
        if self.heartbeat: self.heartbeat.stop()

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
        payload = self.buffer[:self.header.dlen]
        self.buffer = self.buffer[self.header.dlen:]
        self.mode = MMPMode.Header 

        print "[+] Payload: %s"%payload.encode('hex')

        self.handlePacket(self.header,payload)
        self._extractHeader()

class MMPClientFactory(protocol.ReconnectingClientFactory):
    def __init__(self,callback):
        self.callback = callback
    def buildProtocol(self, address):
        self.resetDelay()
        return MMPProtocol(self.callback)
