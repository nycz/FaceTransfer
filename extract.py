import zlib

from common import *

def read_plugin_info(f, size):
    endpos = f.tell() + size
    length = r_uint8(f)
    plugins = []
    for _ in range(length):
        l = r_uint16(f)
        plugins.append(f.read(l).decode())
    return plugins

def read_formid_array(f):
    fidcount = r_uint32(f)
    return [r_uint32(f) for x in range(fidcount)]

def find_player_changeform(f, cfcount):
    """
    Go through all ChangeForms until the player is found and return it.
    """
    for i in range(cfcount):
        rawfid = bytearray(f.read(3))
        fid = ((rawfid[0]&63)<<16) + (rawfid[1]<<8) + rawfid[2]
        flags = r_uint32(f)
        cftype = r_uint8(f)
        lengthsize = (8, 16, 32)[cftype >> 6]
        ftype = cftype & 63
        version = r_uint8(f)
        ln1 = r_uint(lengthsize, f)
        r_uint(lengthsize, f)
        data = f.read(ln1)
        if fid == 0x7 and ftype == 9:
            return data, flags

def extract_player_data(data, flags, fidarray, pluginlist):
    # Python 2/3 compatability shit
    if isinstance(data[0], int):
        data = list(data)
    else:
        data = list(map(ord, data))
    flags = list(map(int, bin(flags)[2:].zfill(32)[::-1]))
    required_plugins = set()
    out = {}
    def add(desc, width):
        out[desc] = data[:width]
        del data[:width]
    # Basedata (incl level)
    if flags[1]:
        del data[:24]
    # Factions
    if flags[6]:
        l = int(data[0]) + 1
        del data[:l]
    if flags[4]:
        print(len(data))
        # Spells
        l = int(int(data[0])*0.75) + 2
        print(l)
        del data[:l]
        # Shouts
        l = int(int(data[0])*0.75) + 1
        del data[:l]
    # AIData
    if flags[3]:
        del data[:20]
    # Name
    if flags[5]:
        l = data[0] + data[1]*2**8
        del data[:2]
        add('name', l)
    # Skills and stats
    if flags[9]:
        del data[:52]
    # Race
    if flags[25]:
        del data[0]
    # Unknown, usually 1
    del data[0]
    # Facial data
    if flags[11]:
        out['hair color'] = formid(data[:3], fidarray, pluginlist)
        required_plugins.add(out['hair color'][0])
        del data[:3]
        add('skin color', 3)
        del data[0]
        out['head texture'] = formid(data[:3], fidarray, pluginlist)
        required_plugins.add(out['head texture'][0])
        del data[:3]
        l = int(int(data[0])*0.75)
        del data[0]
        headparts = []
        for x in range(0,l,3):
            headparts.append(formid(data[x:x+3], fidarray, pluginlist))
            required_plugins.add(headparts[-1][0])
        out['headparts'] = headparts
        del data[:l]
        add('unknown1', 5)
        add('face morph values', 76)
        add('faceparts', 20)
    if flags[24]:
        add('female', 1)
    required_plugins.discard("")
    return out, list(required_plugins)



def extract_data(fname):
    with open(fname, 'rb') as f:
        # TESV_SAVEGAME
        f.seek(13)
        # Go to end of the header, and read thumbsize
        headersize = r_uint32(f)
        f.seek(headersize-2*4, 1)
        shotw, shoth = r_uint32(f), r_uint32(f)
        # Screenshot
        f.seek(3*shotw*shoth, 1)
        # FormVersion
        f.seek(1, 1)
        # Plugininfo
        plugininfosize = r_uint32(f)
        plugininfo = read_plugin_info(f, plugininfosize)
        # File Location Table
        fidcountoffset = r_uint32(f)
        f.seek(3*4, 1)
        # ChangeForm
        cfoffset = r_uint32(f)
        cfend = r_uint32(f)
        f.seek(3*4, 1)
        cfcount = r_uint32(f)
        # FormID Array
        f.seek(fidcountoffset)
        fidarray = read_formid_array(f)
        # Player ChangeForm
        f.seek(cfoffset)
        player, playerflags = find_player_changeform(f, cfcount)

    ucdata = zlib.decompress(player)
    playerdata, required_plugins\
        = extract_player_data(ucdata, playerflags, fidarray, plugininfo)
    return plugininfo, fidarray, playerdata, playerflags, required_plugins