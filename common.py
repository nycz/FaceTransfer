import struct

from io import BufferedReader
from typing import Any, IO, Sequence, Tuple

def r_uint(n: int, f: IO[bytes]) -> int:
    x = {8:'B', 16:'H', 32:'I'}
    return struct.unpack(x[n], f.read(int(n/8)))[0]

def uint(n: int, b: bytes) -> int:
    x = {8:'B', 16:'H', 32:'I'}
    return struct.unpack(x[n], b[:n//8])[0]

def r_uint8(f: IO[bytes]) -> int:
    return uint8(f.read(1))

def uint8(b: bytes) -> int:
    return struct.unpack('B', b)[0]

def r_uint16(f: IO[bytes]) -> int:
    return uint16(f.read(2))

def uint16(b: bytes) -> int:
    return struct.unpack('H', b)[0]

def r_uint32(f: IO[bytes]) -> int:
    return uint32(f.read(4))

def uint32(b: bytes) -> int:
    return struct.unpack('I', b)[0]

def r_refid(f: IO[bytes], fidarray: Sequence[int]) -> int:
    return parse_refid(f.read(3), fidarray)

def parse_refid(b: bytes, fidarray: Sequence[int]) -> int:
    """
    Return the correctly parsed formID using the upper two bits of the byte
    array.

    fidarray is a list of formIDs from the ESPMs.
    """
    # Get the upper two bits
    head = b[0] >> 6
    # Get the actual refID from the lower 22 bits (three bytes minus two bits)
    refid = ((b[0]&63)<<16) + (b[1]<<8) + b[2]
    # Special weird case
    if head == 0 and refid == 0:
        return 0
    # The refID is an index in the formID array (ie from a plugin).
    elif head == 0:
        return fidarray[refid-1]
    # The refID is a normal one from the main game ESM
    elif head == 1:
        return refid
    # The refID is created (for example an arrow)
    elif head == 2:
        return 0xff000000 + refid
    # This should never happen
    else:
        raise AssertionError('refid head is {}'.format(head))

def get_formid_data(b: bytes, fidarray: Sequence[int], pluginlist: Sequence[str]) -> Tuple[str, int]:
    """
    Get a refID, parse it and return the actual formID coupled with the plugin
    name if applicable.

    If the formID is from the main game ESM, return it.
    If the formID is from a plugin, return the name of the plugin and the
    formID without the plugin index (the first byte) since the plugin may not
    have the same place in the new ESS' load order.
    """
    fid = parse_refid(b, fidarray)
    # If the first byte is 0, the formID is from the main game ESM
    if fid < 0x01000000:
        return None, fid
    # If the first byte is 255, the formID is created in-game.
    elif fid > 0xff000000:
        return None, fid
    # Otherwise it's from a plugin, and the first byte is the index number.
    else:
        return pluginlist[fid>>24], fid & 0xffffff

#if __name__ == '__main__':
#    parse_refid(b'arst', 123)
