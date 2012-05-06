from twisted.internet import reactor
import mrim_protocol
import telnetlib
import sys

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

    reactor.connectTCP(host, port, mrim_protocol.MRIMClientFactory())
    reactor.run()
    
if __name__ == "__main__":
    main()
