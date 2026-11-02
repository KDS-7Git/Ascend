"""In-memory register model; not a Modbus network stack or industrial device."""
REGISTERS={10:50,11:1}
def read(address):
    if address not in REGISTERS: raise KeyError("unknown register")
    return REGISTERS[address]
if __name__ == "__main__":
    for address in (10,11): print(address,read(address))
