"""Submit one synthetic local message over verified TLS, or test a named denial."""
import argparse
import getpass
from pathlib import Path
import smtplib
import ssl

parser=argparse.ArgumentParser(description=__doc__)
mode=parser.add_mutually_exclusive_group()
mode.add_argument("--unauthenticated",action="store_true")
mode.add_argument("--wrong-password",action="store_true")
args=parser.parse_args()
context=ssl.create_default_context(cafile=str(Path("work/tls/cert.pem")))
password=None if args.unauthenticated else ("intentionally-wrong-lab-password" if args.wrong_password else getpass.getpass("Synthetic labmail password: "))
try:
    with smtplib.SMTP("localhost",587,timeout=5) as client:
        client.ehlo("client.relay.test")
        client.starttls(context=context)
        client.ehlo("client.relay.test")
        if not args.unauthenticated:
            client.login("labmail",password)
        client.sendmail("labmail@relay.test",["labmail@relay.test"],"From: labmail@relay.test\r\nTo: labmail@relay.test\r\nSubject: Local authenticated submission\r\n\r\nSynthetic local mailbox control.\r\n")
except smtplib.SMTPAuthenticationError:
    if not args.wrong_password: raise
    print("Expected wrong-password authentication rejection observed")
except smtplib.SMTPRecipientsRefused as error:
    if not args.unauthenticated: raise
    print("Unauthenticated recipient rejected:",error.recipients)
else:
    if args.unauthenticated or args.wrong_password:
        raise SystemExit("Negative control failed: forbidden submission was accepted")
    print("Synthetic message accepted by local submission; verify its contents through IMAP next")
