#!/usr/bin/env python3

from collections import OrderedDict
from datetime import datetime, timedelta
from functools import partial
import os.path
import pprint
import struct
import traceback
import zlib

from typing import Any, Dict, List, Tuple

from common import parse_refid, get_formid_data, uint, uint8, uint16, uint32

def parse_uint(bits: int, i: int, data: bytes) -> Tuple[int, int]:
    return bits//8, uint(bits, data[i:i+4])

def parse_float32(i: int, data: bytes) -> Tuple[int, float]:
    return 4, struct.unpack('f', data[i:i+4])[0]

def parse_wstring(i: int, data: bytes) -> Tuple[int, str]:
    length = uint16(data[i:i+2])
    return 2 + length, data[i+2:i+2+length].decode()

def parse_vsval(i: int, data: bytes) -> Tuple[int, int]:
    byte1 = data[i]
    # The two rightmost bits of the first byte decides the length of the var
    size = byte1 & 0b11
    if size == 0:
        # uint8
        return 1, byte1 >> 2
    elif size == 1:
        # uint16
        return 2, (byte1 | (data[i+1] << 8)) >> 2
    elif size == 2:
        raise Exception('WELL SHIT the vsval got a uint32. just great')

def parse_bytes(length: int, i: int, data: bytes) -> Tuple[int, str]:
    out = ''
    for byte in data[i:i+length]:
        out += str(byte).zfill(3)
        out += ' '
    return length, out #data[i:i+length]

def parse_bytechunk(chunks: int, chunksize: int, i: int, data: bytes) -> Tuple[int, str]:
    out = ''
    for byte in data[i:i+chunks*chunksize]:
        out += str(byte).zfill(3)
        out += ' '
    return chunks*chunksize, out #data[i:i+chunks*chunksize]

def parse_refids(formidarray: List[int], pluginlist: List[str], refidcount: int,
                 i: int, data: bytes) -> Tuple[int, List[Tuple[str, int]]]:
    formiddata = [] # type: List[Tuple[str, int]]
    for _ in range(refidcount):
        plugin, fid = get_formid_data(data[i:i+3], formidarray, pluginlist)
        formiddata.append((plugin, fid))
        i += 3
    return refidcount*3, formiddata

def parse_factions(formidarray: List[int], pluginlist: List[str], factionsize: int,
                    i: int, data: bytes) -> Tuple[int, List[Tuple[str, int, int]]]:
    factions = [] # type: List[Tuple[str, int, int]]
    factioncount = factionsize // 4
    for _ in range(factioncount):
        plugin, fid = get_formid_data(data[i:i+3], formidarray, pluginlist)
        rank = uint8(data[i+3:i+4])
        factions.append((plugin, fid, rank))
        i += 4
    return factionsize, factions

def parse_filetime(i: int, data: bytes):
    # TODO: this crap
    return 8, data[i:i+8]

def parse_screenshot(game: str, w: int, h: int, i: int, data: bytes) -> Tuple[int, bytes]:
    ln = {'skyrim': 3, 'fallout4': 4}[game]
    return w*h*ln, data[i:i+w*h*ln]

def parse_plugininfo(plugininfosize: int, i: int, data: bytes) -> Tuple[int, List[str]]:
    pluginnum = uint8(data[i:i+1])
    n = i+1
    plugins = [] # type: List[str]
    for _ in range(pluginnum):
        offset, pluginname = parse_wstring(n, data)
        n += offset
        plugins.append(pluginname)
    return plugininfosize, plugins

def parse_formidarray(formidarraycount: int, i: int, data: bytes) -> Tuple[int, List[int]]:
    formids = [] # type: List[int]
    for _ in range(formidarraycount):
        formids.append(uint32(data[i:i+4]))
        i += 4
    return i, formids

def dump_screenshot(w: int, h: int, game: str, imgdata: bytes) -> None:
    from PIL import Image
    mode = {'skyrim': 'RGB', 'fallout4': 'RGBA'}[game]
    img = Image.frombytes(mode, (w,h), imgdata)
    img.save('shotdump.png')


def find_player_changeform(cfcount: int, formidarray: List[int],
                           i: int, data: bytes) -> Tuple[int, Tuple[bytes, int, int]]:
    """
    Go through all ChangeForms until the player is found and return it.

    The format is:
    formID          RefID
    changeFlags     uint32
    type            uint8                   type of form
    version         uint8
    length1         int                     length of the data
    length2         int                     0 or length of uncompressed data
    data            uint8[length1]
    """
    for n in range(cfcount):
        refid = data[i:i+3]
        formid = parse_refid(refid, formidarray)
        i += 3
        flags = uint32(data[i:i+4])
        i += 4
        cftype = uint8(data[i:i+1])
        i += 1
        # Top 2 bits are the size of data lengths (ln1 and ln2)
        lengthsize = [8, 16, 32][cftype >> 6]
        # Lower 6 bits are the type of form
        formtype = cftype & 63
        # The Skyrim version (currently unused)
        version = uint8(data[i:i+1])
        #assert version in [57, 64, 73, 74]
        i += 1
        # The actual length
        ln1 = uint(lengthsize, data[i:i+4])
        i += lengthsize//8
        # Compressed length or 0 if uncompressed
        ln2 = uint(lengthsize, data[i:i+4])
        i += lengthsize//8 + ln1
        if formid == 7 and formtype == 9:
            return 0, (data[i-ln1:i], ln2, flags)



def parse_file(fname: str) -> Tuple[str, Dict[str, Any]]:
    with open(fname, 'rb') as f:
        data = f.read()
    if data[:13] == b'TESV_SAVEGAME':
        game = 'skyrim'
    elif data[:12] == b'FO4_SAVEGAME':
        game = 'fallout4'
    else:
        game = None
    with open('{}.ft'.format(game), 'r') as f:
        instructions = f.read().splitlines()
    vardict = OrderedDict() # type: Dict[str, Any]
    cmds = {
        'uint8': partial(parse_uint, 8),
        'uint16': partial(parse_uint, 16),
        'uint32': partial(parse_uint, 32),
        'float32': parse_float32,
        'wstring': parse_wstring,
        'filetime': parse_filetime,
        'screenshot': partial(parse_screenshot, game),
        'plugininfo': parse_plugininfo,
        'player': find_player_changeform,
        'formidarray': parse_formidarray,
    }
    def parse_arg(arg):
        if arg.startswith('$'):
            return vardict[arg]
        else:
            return int(arg)
    i = 0
    try:
        for line in instructions:
            if line.startswith('#') or not line.strip():
                continue
            cmd, varname, *rawargs = line.split()
            if cmd == 'skip':
                i += parse_arg(varname)
                continue
            elif cmd == 'goto':
                i = parse_arg(varname)
                continue
            elif cmd in cmds:
                func = cmds[cmd]
                args = [parse_arg(x) for x in rawargs] + [i, data]
                offset, value = func(*args) # this stuff has to be done b/c of mypy
                i += offset
                if value is not None:
                    vardict[varname] = value
            else:
                raise SyntaxError('Unknown command: {}'.format(cmd))
        return game, vardict
    except Exception as e:
        traceback.print_exc()
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(vardict)
        print(len(data))


def generate_flags(num: int) -> List[int]:
    return [n for n, x in enumerate(bin(num)[2:][::-1]) if x == '1']

def parse_player(game: str, vardict: Dict[str, Any]):
    if vardict['$player'][1] != 0:
        data = zlib.decompress(vardict['$player'][0])
        assert len(data) == vardict['$player'][1]
    else:
        data = vardict['$player'][0]
    flags = generate_flags(vardict['$player'][2])
    print_bytes(data, flags)
    formidarray = vardict['$formidarray']
    pluginlist = vardict['$plugininfo']
    with open('{}-face.ft'.format(game), 'r') as f:
        instructions = f.read().splitlines()
    pldict = OrderedDict() # type: Dict[str, Any]
    cmds = {
        'uint8': partial(parse_uint, 8),
        'uint16': partial(parse_uint, 16),
        'uint32': partial(parse_uint, 32),
        'float32': parse_float32,
        'wstring': parse_wstring,
        'bytes': parse_bytes,
        'bytechunks': parse_bytechunk,
        'refid': partial(parse_refids, formidarray, pluginlist, 1),
        'refids': partial(parse_refids, formidarray, pluginlist),
        'vsval': parse_vsval,
        'factions': partial(parse_factions, formidarray, pluginlist),
    }
    def parse_arg(arg):
        if arg.startswith('$'):
            return pldict[arg]
        else:
            return int(arg)
    i = 0
    skipthisflag = False
    try:
        for line in instructions:
            if line.startswith('#') or not line.strip():
                continue
            cmd, varname, *rawargs = line.strip().split()
            if skipthisflag and cmd != 'flag':
                continue
            if cmd == 'flag':
                if varname.startswith('!') and int(varname[1:]) in flags:
                    skipthisflag = True
                elif varname.isdigit() and int(varname) not in flags:
                    skipthisflag = True
                else:
                    skipthisflag = False
            elif cmd in cmds:
                func = cmds[cmd]
                args = [parse_arg(x) for x in rawargs] + [i, data]
                offset, value = func(*args) # this stuff has to be done b/c of mypy
                i += offset
                if value is not None:
                    pldict[varname] = value
            else:
                raise SyntaxError('Unknown command: {}'.format(cmd))
        if data[i:]:
            print('REST', data[i:])
    except Exception as e:
        traceback.print_exc()
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(pldict)


def print_bytes(b: bytes, flags: List[int]):
    out = ''
    for byte in b:
        out += str(byte).zfill(3)
        out += ' '
    with open('dump.txt', 'w') as f:
        f.write('[' + ' '.join(map(str, flags)) + ']\n\n\n')
        f.write(out)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('file')
    args = parser.parse_args()
    game, vardict = parse_file(args.file)
    parse_player(game, vardict)



if __name__ == '__main__':
    main()