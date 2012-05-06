from mmptypes import *
import struct

class MMPWrongHeaderData(Exception):
    pass

class MMPHeader(object):
    size = 44 # usual MMP header size as stated in 
              # protocol specification
    format = '7L16B'
    def __init__(self, magic = CS_MAGIC, proto = PROTO_VERSION, seq = 0, msg = 0, dlen = 0):
        self.magic = magic
        self.proto = proto
        self.seq = seq
        self.msg = msg
        self.dlen = dlen
    
    def __str__(self):
        return "{proto: %d, seq: %d, msg: %d, dlen: %d}"%(
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
            raise MMPWrongHeaderDatai, "%d is minimum header size"%cls.size
        # skipping last 16 reserved bytes
        (magic,proto,seq,msg,dlen,fromip,fromport) = struct.unpack(cls.format,data[:-16]) 

        header = cls(magic,proto,seq,msg,dlen)
        header.fromip = fromip
        header.fromport = fromport
        
        return header

    def binary_data(self):
        return struct.pack(format, self.magic,
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
        return header.binary_data()

class MMPServerHelloAckPacket(object):
    msg = MRIM_CS_HELLO_ACK
    def __init__(self, binary_data):
        pass
