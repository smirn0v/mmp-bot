from twisted.internet import reactor
import mmp_protocol
import telnetlib
import sys

class MMPBot(mmp_protocol.MMPCallbackBase):
    def __init__(self):
        super(MMPBot,self).__init__()

    def loginPassword(self):
        return ("johann-the-builder@mail.ru","buildpleasemail")

    def authrizationRequest(self,from_email):
        self.protocol.authorize(from_email)

    def message(self,from_email,message):
        print "%s: %s"%(from_email,message)
        

def server_to_connect():
    telnet = telnetlib.Telnet("mrim.mail.ru",2042)
    address = telnet.read_all()
    telnet.close()

    host,port = address.split(":")

    if host == None or port == None or \
       len(port) < 2 or port[-1] != '\n': 
        return None,None

    port = port[:-1] #trim '\n'
    if not port.isdigit(): return None,None

    return host,int(port) 
     
def main():
    host, port = server_to_connect()
    if host==None or port==None: 
        print "[-] Error: can't receive mrim server to connect"
        sys.exit(-1)
    
    print "[+] Host = %s; Port = %d"%(host,int(port))

    reactor.connectTCP(host, port, mmp_protocol.MMPClientFactory(MMPBot()))
    reactor.run()
    
if __name__ == "__main__":
    main()
