"""
This module contains all low-level game independant functions used to
manipulate and extract data in save game files.
"""

from collections import OrderedDict
import struct
import traceback
import zlib

from typing import Any, Dict, List, Tuple

# ========= Encode/decode functions ==========================================

def uint8(i: int, data: bytes) -> Tuple[int, int]:
    return 1, struct.unpack('B', data[i:i+1])[0]

def encode_uint8(data: int) -> bytes:
    return struct.pack('B', data)

def uint16(i: int, data: bytes) -> Tuple[int, int]:
    return 2, struct.unpack('H', data[i:i+2])[0]

def encode_uint16(data: int) -> bytes:
    return struct.pack('H', data)

def uint32(i: int, data: bytes) -> Tuple[int, int]:
    return 4, struct.unpack('I', data[i:i+4])[0]

def encode_uint32(data: int) -> bytes:
    return struct.pack('I', data)

def float32(i: int, data: bytes) -> Tuple[int, bytes]:
    # Since floats lose a shitload of precision, lets just go with bytes for now
    return 4, data[i:i+4] #struct.unpack('f', data[i:i+4])[0]

def encode_float32(data: bytes) -> bytes:
    return data #struct.pack('f', data)

def wstring(i: int, data: bytes) -> Tuple[int, str]:
    _, length = uint16(i, data)
    return 2 + length, data[i+2:i+2+length].decode('cp1252')

def encode_wstring(data: str) -> bytes:
    btext = data.encode('cp1252')
    length = encode_uint16(len(btext))
    return length + btext

def bytes_(i: int, data: bytes, length=0, end=0) -> Tuple[int, bytes]:
    if length > 0:
        endpoint = i+length
    elif end > 0:
        endpoint = end
    else:
        raise Exception('Invalid arguments to bytes_ typefunc')
    return endpoint-i, data[i:endpoint]

def encode_bytes(data: bytes) -> bytes:
    return data

def formids(i: int, data: bytes, num=0) -> Tuple[int, bytes]:
    return num*4, data[i:i+num*4]

def encode_formids(data: bytes) -> bytes:
    return data

def screenshot(i: int, data: bytes, width=0, height=0, colorlength=0) -> Tuple[int, bytes]:
    assert width*height > 0 and colorlength > 0
    return width*height*colorlength, data[i:i+width*height*colorlength]

def encode_screenshot(data: bytes) -> bytes:
    return data

# ========= Misc functions ===================================================

def flags(i: int, data: bytes) -> List[int]:
    return [n for n, x in enumerate(bin(uint32(i, data)[1])[2:][::-1]) if x == '1']

def encode_flags(flags: List[int]) -> bytes:
    return encode_uint32(sum(pow(2, x) for x in flags))




# ========= Main functions ===================================================

mainlayout = [
    (bytes_, 'magic', {'length': 12, 'game': 'fallout4'}),
    (bytes_, 'magic', {'length': 13, 'game': 'skyrim'}),
    (uint32, 'headersize', {}),
    # Header
    (uint32, 'version', {}),
    (uint32, 'savenumber', {}),
    (wstring, 'playername', {}),
    (uint32, 'playerlevel', {}),
    (wstring, 'playerlocation', {}),
    (wstring, 'gamedate', {}),
    (wstring, 'playerraceeditorid', {}),
    (uint16, 'playersex', {}),
    (float32, 'playercurexp', {}),
    (float32, 'playerlvlupexp', {}),
    (bytes_, 'filetime', {'length': 8}),
    # Screenshot
    (uint32, 'shotwidth', {}),
    (uint32, 'shotheight', {}),
    (screenshot, 'screenshotdata', {'width': 'shotwidth', 'height': 'shotheight', 'colorlength': 4, 'game': 'fallout4'}),
    (screenshot, 'screenshotdata', {'width': 'shotwidth', 'height': 'shotheight', 'colorlength': 3, 'game': 'skyrim'}),
    # Misc stuff
    (uint8, 'formversion', {}),
    (wstring, 'gameversion', {'game': 'fallout4'}),
    (uint32, 'plugininfosize', {}),
    (bytes_, 'plugininfo', {'length': 'plugininfosize'}),
    # File location table
    (uint32, 'formidarraycountoffset', {}),
    (uint32, 'unknowntable3offset', {}),
    (uint32, 'globaldatatable1offset', {}),
    (uint32, 'globaldatatable2offset', {}),
    (uint32, 'changeformsoffset', {}),
    (uint32, 'globaldatatable3offset', {}),
    (bytes_, 'globaldatatablecounts', {'length': 12}),
    (uint32, 'changeformcount', {}),
    (bytes_, 'flttail', {'length': 15*4}),
    # Data tables
    (bytes_, 'globaldatatable1', {'end': 'globaldatatable2offset'}),
    (bytes_, 'globaldatatable2', {'end': 'changeformsoffset'}),
    (bytes_, 'changeforms', {'end': 'globaldatatable3offset'}),
    (bytes_, 'globaldatatable3', {'end': 'formidarraycountoffset'}),
    (uint32, 'formidarraycount', {}),
    (formids, 'formidarray', {'num': 'formidarraycount'}),
    (uint32, 'visitedworldspacearraycount', {}),
    (formids, 'visitedworldspacearray', {'num': 'visitedworldspacearraycount'}),
    (uint32, 'unknown3tablesize', {}),
    (bytes_, 'unknown3table', {'length': 'unknown3tablesize'})
]

playerlayout = [
    ()
]


def parse_changeforms(rawdata: bytes):
    """
    Convert the changeforms table to a useful dict with the different parts of
    the player's changeform and the preceding and succeeding bytes.

    The dict it returns is ready to be passed to encode_changeforms to convert
    it back to bytes.
    """
    def uint(b, sizeflag):
        return struct.unpack(['B', 'H', 'I'][sizeflag], b)[0]
    i = 0
    cfstart = 0
    data = OrderedDict()
    # Go through the changeforms until the player is found
    while True:
        cfstart = i
        refid = rawdata[i:i+3]
        changeflags = flags(i+3, rawdata)
        _, cftype = uint8(i+7, rawdata)
        _, version = uint8(i+8, rawdata)
        i += 9
        lnsize = [1,2,4][cftype >> 6]
        reallength = uint(rawdata[i:i+lnsize], cftype >> 6)
        uncompressedlength = uint(rawdata[i+lnsize:i+lnsize*2], cftype >> 6)
        i += lnsize * 2 + reallength
        # This is the players refid
        if refid == bytes([64,0,7]):
            data['changeformshead'] = rawdata[:cfstart]
            data['playerrefid'] = refid
            data['playerchangeflags'] = changeflags
            data['playercftype'] = cftype & 63
            data['playerversion'] = version
            data['playerreallength'] = reallength
            data['playeruncompressedlength'] = uncompressedlength
            if uncompressedlength:
                data['playerdata'] = zlib.decompress(rawdata[i-reallength:i])
            else:
                data['playerdata'] = rawdata[i-reallength:i]
            data['changeformstail'] = rawdata[i:]
            return data


def encode_changeforms(data: Dict[str, Any]) -> bytes:
    """
    Convert the dict with data from the changeform struct back into a byte
    object, ready to be inserted into the main save data dict.

    This functions takes care of calculating the lengths of the different
    parts in it so the playeruncompressedlength and playerreallength should
    not be modified outside of this function.
    """
    # Only compress the data if the data was compressed before
    if data['playeruncompressedlength']:
        playerdata = zlib.compress(data['playerdata'])
        uncompressedlength = len(data['playerdata'])
    else:
        playerdata = data['playerdata']
        uncompressedlength = 0
    reallength = len(playerdata)
    cftype = data['playercftype']
    # Fix the whole thing with variable uint sizes for the data lengths
    if reallength > 0xffff or uncompressedlength > 0xffff:
        cftype |= 192
        reallength = encode_uint32(reallength)
        uncompressedlength = encode_uint32(uncompressedlength)
    elif reallength > 0xff or uncompressedlength > 0xff:
        cftype |= 64
        reallength = encode_uint16(reallength)
        uncompressedlength = encode_uint16(uncompressedlength)
    else:
        reallength = encode_uint8(reallength)
        uncompressedlength = encode_uint8(uncompressedlength)
    # Build the actual bytechunk
    rawdata = data['changeformshead'] + data['playerrefid']
    rawdata += encode_flags(data['playerchangeflags'])
    rawdata += encode_uint8(cftype)
    rawdata += encode_uint8(data['playerversion'])
    rawdata += reallength + uncompressedlength + playerdata
    rawdata += data['changeformstail']
    return rawdata


def parse_savedata(rawdata: bytes) -> Tuple[str, Dict[str, Any]]:
    """
    Convert the entirety of a save file (as a bytes object) into an ordered
    dict with all the data from the save file in a more accessible format.

    The dict is also ready to be passed to encode_savedata to be converted
    back to a save file.
    """
    if rawdata[:13] == b'TESV_SAVEGAME':
        game = 'skyrim'
    elif rawdata[:12] == b'FO4_SAVEGAME':
        game = 'fallout4'
    else:
        raise Exception('Game not recognized! Magic is "{}"'.format(rawdata[:12].decode()))
    data = OrderedDict() # type: Dict[str, Any]
    i = 0
    for typefunc, key, rawargs in mainlayout:
        # Skip game-specific lines for the wrong game
        if rawargs.get('game', game) != game:
            continue
        # All string args should be variable names and replaced by
        # their values, and the key 'game' should be removed
        # DO NOT EDIT THE FUCKING ARGS DICT DIRECTLY
        # OR EVERYTHING WILL BLOW UP b/c fuck mutability
        args = {k: data[v] if isinstance(v, str) else v
                for k,v in rawargs.items() if k != 'game'}
        offset, data[key] = typefunc(i, rawdata, **args)
        i += offset
    return game, data

def encode_savedata(data: Dict[str, Any]) -> bytes:
    """
    Take a dictionary with the valid structure of a save file (aka the right
    offsets etc) and merge it into bytes ready to be written to the disc as a
    save file.
    """
    if data['magic'] == b'TESV_SAVEGAME':
        game = 'skyrim'
    elif data['magic'] == b'FO4_SAVEGAME':
        game = 'fallout4'
    else:
        raise Exception('Game not recognized! Magic is "{}"'.format(data['magic'].decode()))
    rawdata = bytes()
    def encodefunc(f):
        return globals()['encode_' + f.__name__.rstrip('_')]
    funcs = {name:encodefunc(func) for func, name, args in mainlayout
             if args.get('game', game) == game}
    for key, value in data.items():
        rawvalue = funcs[key](value)
        rawdata += rawvalue
    return rawdata
