#!/usr/bin/env python3

from collections import OrderedDict
from datetime import datetime, timedelta
import os.path
import pprint
import struct
import traceback
import zlib

from typing import Any, Dict, List, Tuple

from common import parse_refid, get_formid_data, uint, uint8, uint16, uint32

def parse_uint(bits: int, i: int, data: bytes) -> Tuple[int, int]:
    return bits//8, uint(bits, data[i:i+4])

def parse_float32(i: int, data: bytes) -> float:
    return struct.unpack('f', data[i:i+4])[0]

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

def parse_refids(refidcount: int, formidarray: List[int], pluginlist: List[str],
                 i: int, data: bytes) -> Tuple[int, List[Tuple[str, int]]]:
    formiddata = [] # type: List[Tuple[str, int]]
    for _ in range(refidcount):
        plugin, fid = get_formid_data(data[i:i+3], formidarray, pluginlist)
        formiddata.append((plugin, fid))
        i += 3
    return refidcount*3, formiddata

def parse_factions(factioncount: int, formidarray: List[int], pluginlist: List[str],
                    i: int, data: bytes) -> Tuple[int, bytes]:
    #TODO
    return factioncount*4, data[i:i+factioncount*4]

def parse_filetime(i: int, data: bytes):
    # TODO: this crap
    return data[i:i+8]

def parse_screenshot(w: int, h: int, i: int, data: bytes) -> Tuple[int, bytes]:
    return w*h*3, data[i:i+w*h*3]

def parse_plugininfo(i: int, data: bytes) -> List[str]:
    pluginnum = uint8(data[i:i+1])
    n = i+1
    plugins = [] # type: List[str]
    for _ in range(pluginnum):
        offset, pluginname = parse_wstring(n, data)
        n += offset
        plugins.append(pluginname)
    return plugins

def parse_formidarray(formidarraycount: int, i: int, data: bytes) -> Tuple[int, List[int]]:
    formids = [] # type: List[int]
    for _ in range(formidarraycount):
        formids.append(uint32(data[i:i+4]))
        i += 4
    return i, formids

def find_player_changeform(cfcount: int, formidarray: List[int],
                           i: int, data: bytes) -> Tuple[bytes, int, int]:
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
        assert version in [57, 64, 73, 74]
        i += 1
        # The actual length
        ln1 = uint(lengthsize, data[i:i+4])
        i += lengthsize//8
        # Compressed length or 0 if uncompressed
        ln2 = uint(lengthsize, data[i:i+4])
        i += lengthsize//8 + ln1
        if formid == 7 and formtype == 9:
            return data[i-ln1:i], ln2, flags



def parse_file(fname: str) -> Dict[str, Any]:
    with open('skyrim.sft', 'r') as f:
        instructions = f.read().splitlines()
    with open(fname, 'rb') as f:
        data = f.read()
    vardict = OrderedDict() # type: Dict[str, Any]
    i = 0
    for line in instructions:
        if line.startswith('#') or not line.strip():
            continue
        cmd, *args = line.split()
        if cmd == 'skip':
            if args[0].startswith('$'):
                i += vardict[args[0]]
            else:
                i += int(args[0])
        elif cmd == 'goto':
            if args[0].startswith('$'):
                i = vardict[args[0]]
            else:
                i = int(args[0])
        elif cmd.startswith('uint'):
            offset, vardict[args[0]] = parse_uint(int(cmd[4:]), i, data)
            i += offset
        elif cmd == 'float32':
            vardict[args[0]] = parse_float32(i, data)
            i += 4
        elif cmd == 'wstring':
            offset, vardict[args[0]] = parse_wstring(i, data)
            i += offset
        elif cmd == 'filetime':
            vardict[args[0]] = parse_filetime(i, data)
            i += 8
        elif cmd == 'screenshot':
            w, h = vardict[args[1]], vardict[args[2]]
            offset, vardict[args[0]] = parse_screenshot(w, h, i, data)
            i += offset
        elif cmd == 'plugininfo':
            vardict[args[0]] = parse_plugininfo(i, data)
            i += vardict[args[1]]
        elif cmd == 'player':
            vardict[args[0]] = find_player_changeform(vardict[args[1]], vardict[args[2]], i, data)
        elif cmd == 'formidarray':
            offset, vardict[args[0]] = parse_formidarray(vardict[args[1]], i, data)
            i += offset
        else:
            raise SyntaxError('Unknown command: {}'.format(cmd))
    return vardict

    #except Exception as e:
    #    error = True
    #    print('ERROR', e)
    #vardict['$screenshotdata'] = 'LOLSCREENSHOT'
    #vardict['$formidarray'] = 'FORMIDARRAY YO'
    #vardict['$plugininfo'] = 'PLUGINS YO'
    #pp = pprint.PrettyPrinter(indent=4)
    #pp.pprint(vardict)
    #if error:
    #    print('\n !!!!! ERROR !!!!!')

def generate_flags(num: int) -> List[int]:
    return [n for n, x in enumerate(bin(num)[2:][::-1]) if x == '1']

def parse_player(vardict: Dict[str, Any]):
    if vardict['$player'][1] != 0:
        data = zlib.decompress(vardict['$player'][0])
        assert len(data) == vardict['$player'][1]
    else:
        data = vardict['$player'][0]
    flags = generate_flags(vardict['$player'][2])
    formidarray = vardict['$formidarray']
    pluginlist = vardict['$plugininfo']
    with open('skyrim-face.sft', 'r') as f:
        instructions = f.read().splitlines()
    pldict = OrderedDict() # type: Dict[str, Any]
    i = 0
    skipthisflag = False
    try:
        for line in instructions:
            if line.startswith('#') or not line.strip():
                continue
            cmd, *args = line.strip().split()
            if skipthisflag and cmd != 'flag':
                continue
            if cmd == 'flag':
                if int(args[0]) not in flags:
                    skipthisflag = True
                else:
                    skipthisflag = False
            elif cmd.startswith('uint'):
                offset, pldict[args[0]] = parse_uint(int(cmd[4:]), i, data)
                i += offset
            elif cmd == 'bytes':
                if args[1].isdigit():
                    ln = int(args[1])
                else:
                    ln = pldict[args[1]]
                pldict[args[0]] = data[i:i+ln]
                i += ln
            elif cmd == 'wstring':
                offset, pldict[args[0]] = parse_wstring(i, data)
                i += offset
            elif cmd == 'vsval':
                offset, pldict[args[0]] = parse_vsval(i, data)
                i += offset
            elif cmd == 'refids':
                if args[1].isdigit():
                    count = int(args[1])
                else:
                    count = pldict[args[1]]
                offset, pldict[args[0]] = parse_refids(count, formidarray, pluginlist, i, data)
                i += offset
            elif cmd == 'refid':
                offset, pldict[args[0]] = parse_refids(1, formidarray, pluginlist, i, data)
                i += offset
            elif cmd == 'factions':
                count = pldict[args[1]]//4
                offset, pldict[args[0]] = parse_factions(count, formidarray, pluginlist, i, data)
                i += offset
            else:
                raise SyntaxError('Unknown command: {}'.format(cmd))
        if data[i:]:
            print('REST', data[i:])
    except Exception as e:
        traceback.print_exc()
    finally:
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(pldict)



def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('file')
    args = parser.parse_args()
    vardict = parse_file(args.file)
    parse_player(vardict)



if __name__ == '__main__':
    main()