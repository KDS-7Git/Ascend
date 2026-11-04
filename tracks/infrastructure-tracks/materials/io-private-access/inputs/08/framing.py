"""A bounded framing exercise, not an encrypted tunnel."""
import struct
MAX=65536
def encode(data):
    if len(data)>MAX: raise ValueError("frame too large")
    return struct.pack("!I",len(data))+data
def decode(frame):
    if len(frame)<4: raise ValueError("missing header")
    length=struct.unpack("!I",frame[:4])[0]
    if length>MAX or len(frame)!=length+4: raise ValueError("invalid length")
    return frame[4:]
if __name__=="__main__":
    assert decode(encode(b"relay"))==b"relay"
    try: decode(struct.pack("!I",MAX+1))
    except ValueError: print("oversized input rejected")
    else: raise SystemExit("negative control failed")
    print("bounded framing round trip passed; no network or cryptography executed")
