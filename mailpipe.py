#!/usr/bin/env python3

import sys
import xmlrpc.client

if __name__ == "__main__":
    s=sys.stdin.buffer.read()
    if type(s) is bytes:
        s=s.decode("utf-8")

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
