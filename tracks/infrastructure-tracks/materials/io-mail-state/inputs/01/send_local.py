from pathlib import Path
import smtplib
raw=(Path(__file__).parent/"message.eml").read_bytes()
with smtplib.SMTP("127.0.0.1",1025,timeout=3) as client:
    client.sendmail("envelope@relay.test",["learner@relay.test"],raw)
print("Synthetic message submitted to local Mailpit only")
