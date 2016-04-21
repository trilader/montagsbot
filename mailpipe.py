#!/usr/bin/env python3

import sys
import xmlrpc.client

if __name__ == "__main__":
    s=""
    for line in sys.stdin:
        s+=line

    #print("Mail is:",s)

    remote = xmlrpc.client.ServerProxy("http://localhost:4711")
    try:
        remote.handle_reply_mail(s)
    except xmlrpc.client.Fault as err:
        print("A fault occurred")
        print("Fault code: %d" % err.faultCode)
        print("Fault string: %s" % err.faultString)
    except Exception as ex:
        print("Error:",ex)
