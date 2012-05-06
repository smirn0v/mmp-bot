import mrim_protocol
import telnetlib

def main():
    telnet = telnetlib.Telnet("mrim.mail.ru",2042)
    address = telnet.read_all()
    telnet.close()

    host,port = address.split(":")
    
    if !host or !port: 
        print "Can't receive mrim server to connect"
        die
    
    print "host = %s, port = %d"%(host,int(port))
    
if __name__ == "__main__":
    main()
