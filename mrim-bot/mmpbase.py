from mmptypes import *
import struct

MMP_CLIENT_STRING = "MRIM Johann Bot v0.1"

class MMPWrongHeaderData(Exception):
    pass

class MMPMalformedPacket(Exception):
    pass

def unpack_lps(data):
    size_length = struct.calcsize('I')
    if len(data) < size_length:
        raise MMPMalformedPacket,"Can't extract string from data"
    string_length = struct.unpack('I',data[:size_length])[0]
    data = data[size_length:] 
    if len(data) < string_length:
        raise MMPMalformedPacket("Incorrect string length received (string length = %d data length = %d)"%(string_length,len(data)))
    string = struct.unpack("%ds"%string_length,data[:string_length])
    data = data[string_length:]
    return string

class MMPHeader(object):
    size = 44 # usual MMP header size as stated in 
              # protocol specification
    format = '7I16B'
    def __init__(self, magic = CS_MAGIC, proto = PROTO_VERSION, seq = 0, msg = 0, dlen = 0):
        self.magic = magic
        self.proto = proto
        self.seq = seq
        self.msg = msg
        self.dlen = dlen
    
    def __str__(self):
        return "{magic: 0x%X, proto: 0x%X, seq: %d, msg: 0x%X, dlen: %d}"%(
                                                            self.magic,
                                                            self.proto,
                                                            self.seq,
                                                            self.msg,
                                                            self.dlen
                                                         )
    def __repr__(self):
        return self.__str__()

    @classmethod
    def from_binary_data(cls,data):
        if len(data) < cls.size:
            raise MMPWrongHeaderData, "%d is minimum header size (%d given)"%(cls.size,len(data))

        # just skip 'reserved' 16 bytes
        (magic,proto,seq,msg,dlen,fromip,fromport) = struct.unpack(cls.format,data)[:-16]

        header = cls(magic,proto,seq,msg,dlen)
        header.fromip = fromip
        header.fromport = fromport
        
        return header

    def binary_data(self):
        return struct.pack(MMPHeader.format, self.magic,
                                             self.proto,
                                             self.seq,
                                             self.msg,
                                             self.dlen,
                                             *([0]*18))

class MMPClientHelloPacket(object):
    msg = MRIM_CS_HELLO
    def __init__(self,header):
        self.header = header
        self.header.msg = self.__class__.msg
        self.header.dlen = 0
    def binary_data(self):
        return self.header.binary_data()

class MMPClientLogin2Packet(object):
    msg = MRIM_CS_LOGIN2
    def __init__(self,header,email,password):
        self.header = header
        self.header.msg = self.__class__.msg
        self.email = email
        self.password = password
        self.header.dlen = struct.calcsize('4I')+len(email)+len(password)+len(MMP_CLIENT_STRING)
    def binary_data(self):
        header_data = self.header.binary_data()
        payload = ""
        payload += struct.pack('I',len(self.email)) + self.email
        payload += struct.pack('I',len(self.password)) + self.password
        payload += struct.pack('I',STATUS_ONLINE)
        payload += struct.pack('I',len(MMP_CLIENT_STRING)) + MMP_CLIENT_STRING
        return header_data+payload

class MMPServerHelloAckPacket(object):
    msg = MRIM_CS_HELLO_ACK
    def __init__(self, header, binary_data):
        self.header = header
        if len(binary_data) != struct.calcsize('I'):
            raise MMPMalformedPacket, "Wrong size of HelloAck payload"
        self.interval = struct.unpack('I',binary_data)

class MMPServerLoginAckPacket(object):
    msg = MRIM_CS_LOGIN_ACK
    def __init__(self, header, binary_data):
        self.header = header

class MMPServerLoginRejPacket(object):
    msg = MRIM_CS_LOGIN_REJ
    def __init__(self, header, binary_data):
        self.header = header
        self.reason = unpack_lps(binary_data) 
