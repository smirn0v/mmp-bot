#
# Alexander Smirnov (alexander@smirn0v.ru)
#
from mmptypes import *
import struct

__metaclass__  = type

MMP_CLIENT_STRING = "MRIM Johann Bot v0.1"

class MMPWrongHeaderData(Exception):
    pass

class MMPMalformedPacket(Exception):
    pass

class MMPHeader:
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

class MMPGroup:
    def __init__(self,flags,name):
        self.flags = flags
        self.name = name

class MMPContact:
    def __init__(self,flags,group,address,nickname,server_flags,status):
        self.flags = flags
        self.group = group
        self.address = address
        self.nickname = nickname
        self.server_flags = server_flags
        self.status = status

class PackingMixin:
    def unpack_lps(self):
        size_length = struct.calcsize('I')
        if len(self.binary_data) < size_length:
            raise MMPMalformedPacket,"Can't extract string from binary_data"
        string_length = struct.unpack('I',self.binary_data[:size_length])[0]
        self.binary_data = self.binary_data[size_length:] 
        if len(self.binary_data) < string_length:
            raise MMPMalformedPacket,"Incorrect string length received"
        string = struct.unpack("%ds"%string_length,self.binary_data[:string_length])[0]
        string = string.decode('cp1251').encode('utf8')
        self.binary_data = self.binary_data[string_length:]
        return string

    def unpack_uint(self):
        size = struct.calcsize('I')
        if len(self.binary_data) < size:
            raise MMPMalformedPacket,"Can't extract unsinged int, not enough binary_data"
        result = struct.unpack('I',self.binary_data[:size])[0]
        self.binary_data = self.binary_data[size:] 
        return result

    def unpack_zstring(self):
        ''' unpack zero-ended string '''
        zero_index = self.binary_data.index('\0')
        result = self.binary_data[:zero_index].decode('cp1251').encode('utf8')
        self.binary_data = self.binary_data[zero_index+1:]
        return result

    def unpack_with_mask(self,mask):
        result = []
        for symbol in mask:
            if symbol=='u': result.append(self.unpack_uint())
            elif symbol=='s': result.append(self.unpack_lps())
            elif symbol=='z': result.append(self.unpack_zstring())
            else: raise MMPMalformedPacket,"Unknown mask"
        return tuple(result)

    def pack_lps(self,string):
        return struct.pack('I',len(string)) + string

    def pack_uint(self,value):
        return struct.pack('I',value)

class MMPClientMessagePacket(PackingMixin):
    msg = MRIM_CS_MESSAGE
    def __init__(self,header,flags,to_email,message):
        """ 
        message should be given in ascii
        rtf messages not supported
        """
        self.header = header
        self.header.msg = self.__class__.msg
        self.flags = flags
        self.to_email = to_email
        self.message = message
        self.header.dlen = len(self.binary_data()) - MMPHeader.size

    def binary_data(self):
        data  = self.header.binary_data()
        data += self.pack_uint(self.flags) 
        data += self.pack_lps(self.to_email)
        data += self.pack_lps(self.message)
        return data

class MMPClientAuthorizePacket(PackingMixin):
    msg = MRIM_CS_AUTHORIZE
    def __init__(self,header,email):
        self.header = header
        self.header.msg = self.__class__.msg
        self.email = email
        self.header.dlen = len(self.binary_data()) - MMPHeader.size 
    def binary_data(self):
        return self.header.binary_data()+self.pack_lps(self.email)

class MMPClientPingPacket:
    msg = MRIM_CS_PING
    def __init__(self,header):
        self.header = header
        self.header.msg = self.__class__.msg
        self.header.dlen = 0

    def binary_data(self):
        return self.header.binary_data()

class MMPClientHelloPacket:
    msg = MRIM_CS_HELLO
    def __init__(self,header):
        self.header = header
        self.header.msg = self.__class__.msg
        self.header.dlen = 0
    def binary_data(self):
        return self.header.binary_data()

class MMPClientLogin2Packet(PackingMixin):
    msg = MRIM_CS_LOGIN2
    def __init__(self,header,email,password):
        self.header = header
        self.header.msg = self.__class__.msg
        self.email = email
        self.password = password
        self.header.dlen = len(self.binary_data()) - MMPHeader.size 
    def binary_data(self):
        data = self.header.binary_data()
        data += self.pack_lps(self.email)
        data += self.pack_lps(self.password)
        data += self.pack_uint(STATUS_ONLINE)
        data += self.pack_lps(MMP_CLIENT_STRING)
        return data

class MMPClientMessageRecvPacket(PackingMixin):
    msg = MRIM_CS_MESSAGE_RECV
    def __init__(self,header,from_email,msgid):
        self.header = header
        self.header.msg = self.__class__.msg 
        self.from_email = from_email
        self.msgid = msgid
        self.header.dlen = len(self.binary_data()) - MMPHeader.size
    def binary_data(self):
        data = self.header.binary_data()
        data += self.pack_lps(self.from_email) 
        data += self.pack_uint(self.msgid)
        return data

class MMPServerHelloAckPacket(PackingMixin):
    msg = MRIM_CS_HELLO_ACK
    def __init__(self, header, binary_data):
        self.header = header
        self.binary_data = binary_data
        self.interval = self.unpack_uint()

class MMPServerLoginAckPacket(PackingMixin):
    msg = MRIM_CS_LOGIN_ACK
    def __init__(self, header, binary_data):
        self.header = header

class MMPServerLoginRejPacket(PackingMixin):
    msg = MRIM_CS_LOGIN_REJ
    def __init__(self, header, binary_data):
        self.header = header
        self.binary_data = binary_data
        self.reason = unpack_lps(binary_data) 

class MMPServerMessageAckPacket(PackingMixin):
    msg = MRIM_CS_MESSAGE_ACK
    def __init__(self, header, binary_data):
        self.header = header
        self.binary_data = binary_data
        self.msgid = self.unpack_uint()
        self.flags = self.unpack_uint()
        self.from_email = self.unpack_lps()
        self.message = self.unpack_lps()
        #if self.flag_set(MESSAGE_FLAG_RTF):
        #    self.rtf_message = self.unpack_lps()
    def flag_set(self,flag):
        return (self.flags | flag) == self.flags
    def simple_message(self):
        return  not self.flag_set(MESSAGE_FLAG_SYSTEM)  and \
                not self.flag_set(MESSAGE_FLAG_CONTACT) and \
                not self.flag_set(MESSAGE_FLAG_NOTIFY) and \
                not self.flag_set(MESSAGE_FLAG_AUTHORIZE)

class MMPServerContactListPacket(PackingMixin):
    msg = MRIM_CS_CONTACT_LIST2
    def __init__(self, header, binary_data):
        self.header = header
        self.binary_data = binary_data
        self.status = self.unpack_uint()
        self.groups_number = self.unpack_uint()
        self.group_mask = self.unpack_lps()
        self.contacts_mask = self.unpack_lps()

        self.groups = []
        self.contacts = []
        for i in range(self.groups_number):
            self.groups += [MMPGroup(self.unpack_uint(),self.unpack_lps())]
            self.unpack_with_mask(self.group_mask[2:])
        while len(self.binary_data) > 0:
            flags = self.unpack_uint()
            group = self.unpack_uint()
            address = self.unpack_lps()
            nick = self.unpack_lps()
            server_flags = self.unpack_uint()
            status = self.unpack_uint()
            self.contacts += [MMPContact(flags,group,address,nick,server_flags,status)]
            self.unpack_with_mask(self.contacts_mask[6:])
