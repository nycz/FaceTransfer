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

    # flag, length or function to get length, name to save it to, option
    dynlen_refids = lambda x: (int(int(x[0])*0.75), 1)
    dynlen_factions = lambda x: (int(x[0]), 1)
    dynlen_name = lambda x: (x[0]+(x[1]<<8), 2)
    datalist = [
        (1,    24,              None,                None), # Basedata
        (6,    dynlen_factions, None,                None), # Factions
        (4,    dynlen_refids,   None,                None), # Spells
        (4,    1,               None,                None),
        (4,    dynlen_refids,   None,                None), # Shouts
        (3,    20,              None,                None), # AIData
        (5,    dynlen_name,    'name',               None),
        (9,    52,              None,                None), # Skills and stats
        (25,   6,              'race',              'formid'),
        (None, 1,               None,                None),
        (11,   3,              'hair color',        'formid'),
        (11,   3,              'skin color',         None),
        (11,   1,               None,                None),
        (11,   3,              'head texture',      'formid'),
        (11,   dynlen_refids,  'headparts',         'formid'),
        (11,   5,              'unknown1',           None),
        (11,   76,             'face morph values',  None),
        (11,   20,             'faceparts',          None),
        (24,   1,              'female',             None)
    ]

    for flag, length, savename, option in datalist:
        if flag is not None and not flags[flag]:
            continue
        offset = 0
        if not isinstance(length, int):
            length, offset = length(data)
        if savename:
            if option == 'formid':
                d = data[offset:length+offset]
                l = []
                for n in range(0,len(d),3):
                    l.append(formid(d[n:n+3], fidarray, pluginlist))
                    required_plugins.add(l[-1][0])
                out[savename] = l if len(l) > 1 else l[0]
            else:
                out[savename] = data[offset:length+offset]
        del data[:length+offset]

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