#!/usr/bin/env python
# -*- coding: utf8 -*-

from scapy.all import *
from mmpbase import *
import sys
import struct
import os

def traceback():
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    print(exc_type, fname, exc_tb.tb_lineno)

def ascii_only(s): 
    res = ""
    for c in s:
        if ord(c) >= 0x20 and ord(c) < 0x7F:
            res += c
        else:
            res += "."
    return res

def main():
    pl = rdpcap("agent.pcap")

    supported_packets = [ 
                          MMPServerMessageAckPacket,
                          MMPClientAuthorizePacket,
                          MMPClientMessageRecvPacket,
                          MMPClientMessagePacket,
                          MMPClientAddContact
                        ]
    
    for p in pl:
        try:
            magic = struct.unpack('I',str(p[TCP].payload)[:4])[0]
            if magic!=0xdeadbeef: continue

            header = str(p[TCP].payload)[:44]
            header = MMPHeader.from_binary_data(header)
            print
            print header
            payload = str(p[TCP].payload)[44:]
            print "{payload = %s}"%payload.encode('hex')
            print "{ascii-payload = %s}"%ascii_only(payload)
            for sp in supported_packets:
                if sp.msg == header.msg:
                    mrap = None
                    try:
                        mrap = sp(header,payload)
                    except: pass
                    try:
                        mrap = sp(header,binary_data = payload)
                    except: pass 
                    if mrap is not None:
                        print mrap
        except Exception as e:
            #traceback()
            pass

if __name__ == "__main__":
    main()
