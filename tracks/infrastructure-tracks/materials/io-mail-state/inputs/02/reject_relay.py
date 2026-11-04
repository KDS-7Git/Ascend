"""Observe one unauthorized RCPT rejection at the owned local MTA; no DATA sent."""
import smtplib
with smtplib.SMTP("127.0.0.1", 25, timeout=3, source_address=("127.0.0.2", 0)) as client:
    client.ehlo("client.relay.test")
    code, detail = client.mail("sender@relay.test")
    if code != 250:
        raise SystemExit("MAIL was rejected before the intended relay-policy control")
    code, detail = client.rcpt("recipient@unowned.example.invalid")
    print("RCPT", code, detail.decode(errors="replace"))
    client.rset()
    if code not in (450, 454, 550, 554):
        raise SystemExit("Expected an unauthorized relay rejection; inspect policy before proceeding")
print("Recipient was rejected before DATA; inspect SMTP status/text to confirm relay-policy cause")
