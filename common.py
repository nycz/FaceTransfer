import struct

def r_uint(n, f):
    x = {8:'B', 16:'H', 32:'I'}
    return struct.unpack(x[n], f.read(int(n/8)))[0]

def r_uint8(f):
    return uint8(f.read(1))

def uint8(b):
    return struct.unpack('B', b)[0]

def r_uint16(f):
    return uint16(f.read(2))

def uint16(b):
    return struct.unpack('H', b)[0]

def r_uint32(f):
    return uint32(f.read(4))

def uint32(b):
    return struct.unpack('I', b)[0]

def r_refid(f, fidarray):
    return parse_refid(bytearray(f.read(3)), fidarray)

def parse_refid(b, fidarray):
    head = b[0] >> 6
    refid = b[2] + b[1]*2**8 + (b[0]&63)*2**16
    fid = fidarray[refid-1] if head == 0 else None
    return (fid, refid, 0xff000000 + refid)[head]
