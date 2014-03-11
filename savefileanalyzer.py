import os
import struct
import zlib



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
    b = bytearray(f.read(3))
    head = b[0] >> 6
    out = b[2] + b[1]*2**8 + (b[0]&63)*2**16
    if head == 0:
        return fidarray[out-1]
    if head == 2:
        out += 0xff000000
    return out

def gen_flags(num):
    out = []
    s = str(bin(num))[2:][::-1]
    for n, i in enumerate(s):
        if i == '1':
            out.append(str(n))
    return str(bin(num))+'   '+','.join(out)

def read_changeform(f, fidarray):
    # formID
    refid = r_refid(f, fidarray)
    # changeFlags
    flags = gen_flags(r_uint32(f))

    cftype = r_uint8(f)
    if cftype >> 6 == 2:
        lengthsize = 32
    elif cftype >> 6 == 1:
        lengthsize = 16
    else:
        lengthsize = 8
    ftype = cftype & 63
    version = r_uint8(f)
    ln1 = r_uint(lengthsize, f)
    ln2 = r_uint(lengthsize, f)

    return (refid, ftype), f.tell(), f.read(ln1), flags


def read_plugin_info(f, size):
    endpos = f.tell() + size
    length = r_uint8(f)
    plugins = []
    for _ in range(length):
        l = r_uint16(f)
        plugins.append(f.read(l).decode())
    if endpos != f.tell():
        print(endpos, f.tell())
    return plugins

def read_formid_array(f):
    fidcount = r_uint32(f)
    return [r_uint32(f) for x in range(fidcount)]



def read_savefile(fname):
    with open(fname, 'rb') as f:
        # TESV_SAVEGAME
        f.seek(13)
        headersize = r_uint32(f)
        # Go to end of the header, and read thumbsize
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

        f.seek(fidcountoffset)
        fidarray = read_formid_array(f)

        f.seek(cfoffset)
        for i in range(cfcount):
            (refid, ftype), pos, data, flags = read_changeform(f, fidarray)
            if refid == 0x7 and ftype == 9:
                return plugininfo, fidarray, data, flags
        return []

def format_refid(data, fidarray):
    b = list(map(int, data))
    head = b[0] >> 6
    out = b[2] + b[1]*2**8 + (b[0]&63)*2**16
    refid = str(hex(out))[2:].zfill(6)
    if head == 0:
        fid = fidarray[out-1]
        return '{} ({})'.format(str(hex(fid))[2:].zfill(8), refid)
    else:
        return ('!!', '00', 'ff')[head] + refid

def format_refids(data, fidarray):
    assert len(data)%3 == 0
    out = []
    for n in range(0, len(data), 3):
        out.append(format_refid(data[n:n+3], fidarray))
    return ', '.join(out)

def format_faction_refids(data, fidarray):
    assert len(data)%4 == 0
    out = []
    for n in range(0, len(data), 4):
        out.append(format_refid(data[n:n+3], fidarray) + ':' + str(data[n+3]))
    return ', '.join(out)

def format_data(data, flags, fidarray):
    # Python 2/3 compatability shit
    if isinstance(data[0], int):
        data = list(data)
    else:
        data = list(map(ord, data))
    flags = list(map(int, flags.split()[0][2:].zfill(26)[::-1]))

    out = []
    def add(desc, payload, deloffset):
        out.append((desc, payload))
        del data[:deloffset]

    if flags[1]:
        add('Flag 1', data[:24], 24)

    if flags[6]:
        l = int(data[0]) + 1
        add('Flag 6 (factions)', format_faction_refids(data[1:l], fidarray), l)

    if flags[4]:
        l = int(int(data[0])*0.75) + 1
        add('Flag 4 (spells)', format_refids(data[1:l], fidarray), l+1)
        l = int(int(data[0])*0.75) + 1
        add('Flag 4 (shouts)', format_refids(data[1:l], fidarray), l)

    if flags[3]: # or flags[9]
        add('Flag 3 (aiData)', data[:20], 20)

    if flags[5]:
        l = int(data[0]) + 2 # TODO: test with a longass name
        add('Name', ''.join(map(chr, data[2:l])), l)

    if flags[9]: # or flags[9]
        add('Flag 9 (skills)', data[:18], 18)
        add('Flag 9 (stats data)', data[:34], 34)

    if flags[25]:
        add('Flag 25 (race)', format_refids(data[:6], fidarray), 6)

    add('Unknown (usually 1)', data[0], 1)

    # if flag[11]:
    facial_out, rest_data = format_facial_stuff(data, fidarray)
    out.extend(facial_out)

    if flags[24]:
        add('Female', rest_data[0], 0)
        del rest_data[0]

    if rest_data:
        add('Rest', rest_data, 0)

    text = ''
    for desc, payload in out:
        text += '{}:   {}\n\n'.format(desc, payload)
    return text

def format_rgb(data):
    f = lambda n: str(hex(int(n)))[2:]
    return '#' + ''.join(map(f, data))

def format_facial_stuff(data, fidarray):
    out = []
    def add(desc, payload, deloffset):
        out.append((desc, payload))
        del data[:deloffset]

    add('Hair color', format_refid(data[:3], fidarray), 3)
    add('Skin color', format_rgb(data[:3]), 3)
    add('Unknown (usually 0)', data[0], 1)
    add('Head texture', format_refid(data[:3], fidarray), 3)
    l = int(int(data[0])*0.75) + 1
    add('Headparts', format_refids(data[1:l], fidarray), l)
    add('Unknown', data[:5], 5)
    add('NAM9 (Face morph values)', data[:76], 76)
    add('Unknown (facepart?)', data[:4], 4)
    add('Nose facepart', data[:4], 4)
    add('Unknown (facepart?)', data[:4], 4)
    add('Eyes facepart', data[:4], 4)
    add('Mouth facepart', data[:4], 4)

    return out, data


def format_plugin_info_list(data):
    return ', '.join('{}:{}'.format(hex(n)[2:],x) for n,x in enumerate(data))

def format_fidarray(data):
    return ', '.join(str(hex(x))[2:].zfill(8) for x in data)

def main():
    for fname in os.listdir('saves'):
        plugininfo, fidarray, data, flags = read_savefile('saves/' + fname)
        try:
            ucdata = zlib.decompress(data)
        except zlib.error as e:
            ucdata = data
        else:
            printonlyraw = True
            formatted_data = format_data(ucdata, flags, fidarray)
            # try:
            #     formatted_data = format_data(ucdata, flags, fidarray)
            # except Exception as e:
            #     print(e)
            # else:
            #     printonlyraw = False
            with open('savedumps/' + fname + '.txt', 'w') as f:
                f.write(format_plugin_info_list(plugininfo))
                f.write('\n\n')
                f.write(format_fidarray(fidarray))
                f.write('\n\n')
                f.write(flags)
                if not printonlyraw:
                    f.write('\n\n\n')
                    f.write(formatted_data)
                # f.write('\n\n')
                # f.write(str(list(ucdata)))


if __name__ == '__main__':
    main()