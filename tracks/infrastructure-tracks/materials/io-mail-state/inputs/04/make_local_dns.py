"""Write a loopback-only dnsmasq input from an owned lab DKIM public key."""
from pathlib import Path
import base64
key=Path("work/dkim/lab-public.b64").read_text().strip()
base64.b64decode(key,validate=True)
value="v=DKIM1; k=rsa; p="+key
chunks=[value[i:i+200] for i in range(0,len(value),200)]
lines=["listen-address=127.0.0.1", "bind-interfaces", "no-hosts", "no-resolv", "port=53",
       "address=/mail.relay.test/127.0.0.1", "mx-host=relay.test,mail.relay.test,10",
       'txt-record=relay.test,"v=spf1 ip4:192.0.2.10 -all"',
       'txt-record=_dmarc.relay.test,"v=DMARC1; p=none"',
       "txt-record=lab._domainkey.relay.test,"+",".join('"'+chunk+'"' for chunk in chunks)]
with Path("work/dkim/dnsmasq.conf").open("x") as stream:
    stream.write("\n".join(lines)+"\n")
print("Wrote work/dkim/dnsmasq.conf; review before running a guest-local DNS listener")
