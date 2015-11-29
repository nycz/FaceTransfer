import os
import re
import struct
import zlib

from operator import itemgetter

def r_formid(f):
    b = f.read(3)
    head = b[0] >> 6
    out = b[2] + b[1]*2**8 + (b[0]&63)*2**16
    if head == 2:
        out += 0xff000000
##    if b[2] == 0x7:
##        print(b[0],b[1],b[2])
    return out


def r_uint(n, f):
    x = {8:'B', 16:'H', 32:'I'}
    return struct.unpack(x[n], f.read(int(n/8)))[0]


def r_uint8(f):
    return uint8(f.read(1))

def uint8(b):
    return struct.unpack('B', b)[0]


##def uint16(b):
##    return struct.unpack('>H', b)[0]

def r_uint32(f):
    return uint32(f.read(4))

def uint32(b):
    return struct.unpack('I', b)[0]

def int32(b):
    return struct.unpack('i', b)[0]

def float_(b):
    return struct.unpack('f', b)[0]


def gen_flags(num):
    out = []
    s = str(bin(num))[2:][::-1]
    for n, i in enumerate(s):
        if i == '1':
            out.append(str(n))
    return str(bin(num))+'   '+','.join(out)

print(gen_flags(67))


def read_changeform(f):
    # formID
    fid = r_formid(f)
##    print('FormID: {}'.format(fid))
    # changeFlags
    flags = gen_flags(r_uint32(f))
##    if fid == 0x7:

    cftype = f.read(1)[0]
    if cftype >> 6 == 2:
        lengthsize = 32
    elif cftype >> 6 == 1:
        lengthsize = 16
    else:
        lengthsize = 8
    ftype = cftype & 0b111111
##    print('LnSize: {}'.format(lengthsize))
##    print('Type: {}'.format(cftype & 63))
    version = r_uint8(f)
##    if version != 57:
##        print('Version: {}'.format(version))
    ln1 = r_uint(lengthsize, f)
    ln2 = r_uint(lengthsize, f)
##    if fid == 0x7:
##        print('Lengths: {}, {}'.format(ln1,ln2))
##    if ln2 == 0 and cftype == 9:
##        w = 20
##        print(str(f.read(w)))
##        f.seek(-w, 1)
##    if fid == 0x7:
##        print('cftype7: {}'.format(cftype))

    return (fid, ftype), f.tell(), f.read(ln1), flags


def main(fn):
    with open(fn, 'rb') as f:
        print(f.read(13))
##        f.seek(13)
        headersize = r_uint32(f)
        # Jump to almost at the end of the header, and read the thumbs dimension
        f.seek(headersize-2*4, 1)
        shotw, shoth = r_uint32(f), r_uint32(f)
        # Jump over screenshot
        f.seek(3*shotw*shoth,1)
        # Print formVersion for debug purposes
        print(r_uint8(f))
        # Jump over plugininfo
        f.seek(r_uint32(f), 1)
        # Find the offset to formIDArray
        fidarrayoffset = r_uint32(f)
        # Skip the next tables
        f.seek(3*4, 1)

        cfoffset = r_uint32(f)
        cfend = r_uint32(f)
##        print('CF range: {}-{}'.format(cfoffset, cfend))
        f.seek(3*4, 1)
        cfcount = r_uint32(f)
##        print('cfCount: {}'.format(cfcount))
##        print('Size per cf: {}'.format((cfend-cfoffset)/cfcount))
        f.seek(cfoffset)
##        print()
        # Uh, should be in the first part of Change Form now o_O
        data = []
        for i in range(cfcount):
            (fid, ftype), d, pos, flags = read_changeform(f)
##            if fid in data:
##                print("Wth? {}".format(fid))
            if fid == 0x7 and ftype == 9:
                data = [pos, d, flags]
                return data
        return data
##        count[x] += 1
##    for n,i in enumerate(count):
##        print('{}: {}'.format(n,i))


def sort_after_flags_ish(arr, flags):
    print(list(arr))
    arr = [str(x) for x in list(arr)]
    print('\n')
    out = ''
    flags = flags.split()[0][2:].zfill(26)[::-1]
    # Stuff including level
    if flags[1] == '1':
        out += 'F1[0] as flag:  '+str(bin(int(arr[0])))+'\n'
        out += 'F1:  '+', '.join(arr[:24])+'\n'
        arr = arr[24:]
    # Factions
    if flags[6] == '1':
        l = int(arr[0])
        out += 'F6:  '+', '.join(arr[:l+1])+'\n'
        arr = arr[l+1:]
    # aiData
    if flags[3] == '1': # or 9
        out += 'F3/9:  '+', '.join(arr[:20])+'\n'
        arr = arr[20:]
    # Name
    l = int(arr[0])
    out += 'NAME:  '+', '.join(arr[:l+2])+'\n'
    arr = arr[l+2:]
    # Skills/stat data
    if flags[3] == '1': # or 9
        out += 'F3/9 (skills/stats):  '+', '.join(arr[:52])+'\n'
        arr = arr[52:]
    # Race
    if flags[25] == '1':
        out += 'F25 (race):  '+', '.join(arr[:6])+'\n'
        arr = arr[6:]
    out += arr[0] + '\n'
    out += 'Hair color: '+', '.join(arr[1:4])+'\n'
    out += 'Skin color: '+', '.join(arr[4:7])+'\n'
    out += arr[7] + '\n'
    out += 'Head texture: '+', '.join(arr[8:11])+'\n'
    out += arr[11] + '\n'
    l = int(int(arr[11])*0.75)
    arr = arr[12:]
    out += 'Headmesh, mouth, scar etc:  '+', '.join(arr[:l]) + '\n'
    arr = arr[l:]
    out += ', '.join(arr[:5])+'\n'
    arr = arr[5:]
    out += 'Facegen:  '+', '.join(arr[:76]) + '\n'
    arr = arr[76:]
    out += 'Faceparts~ish:  '+', '.join(arr[:20]) + '\n'
    arr = arr[20:]
    if len(arr) > 0:
        if flags[24] == '1':
            out += 'F24 (female):  '+arr[0] + '\n'
            arr = arr[1:]
        if len(arr) > 0:
            out += 'REST ??:  '+', '.join(arr) + '\n'
    return out


def dump_analysisfile(name, root):
    out = []
    oldflags = None
    savelist = []
    r = re.compile(r'Save \d+ - {} .+? \d\d[.]\d\d[.]\d\d[.]ess$'.format(name))
    for i in os.listdir(root):
        if r.match(i):
            savelist.append((i, int(i.split()[1])))
##    print(savelist)
##    raise Exception
    for i,_ in sorted(savelist, key=itemgetter(1)):
        print(i)
        try:
            d, _, flags = main(root+i)
        except:
            continue
        flagtext = ''
        if flags != oldflags:
            flagtext = ' [changed]'
        try:
            data = zlib.decompress(d)
        except zlib.error as e:
            print(e)
            print(d)
            d_count = 'N/A'
            d2 = str(e)
        else:
            d_count = len(list(data))
            d2 = ', '.join([str(x) for x in list(data)])
        out.extend([i.upper(),'',flags+flagtext,'','Length: {}'.format(d_count),
                    d2,'','','',''])
        oldflags = flags
    with open('{}_generated_analysis.txt'.format(name), 'w') as f:
        for i in out:
            f.write(i+'\n')



base = "saves/"

def dumpsinglesave(fname):
    d, pos, flags = main(fname)
    print(flags)
    try:
        ucdata = zlib.decompress(d)
    except zlib.error as e:
        print(e)
    else:
##        print(list(ucdata))
        print(sort_after_flags_ish(ucdata, flags))

def fid2arr(formid):
    out = []
    out.append(int(formid[2:4], 16)+0x40)
    out.append(int(formid[4:6], 16))
    out.append(int(formid[6:8], 16))
    return out

def arr2fid(rawarr):
    def tohex(num):
        return str(hex(num))[2:].zfill(2)
    arr = rawarr
    if type(rawarr) == type(''):
        arr = [int(x) for x in rawarr.strip(' ,').split(', ')]
    out = '00{}{}{}'.format(tohex(arr[0]-0x40),
                            tohex(arr[1]),
                            tohex(arr[2]))
    return out
##dumpsinglesave(base + "Save 142 - Teerwyn  Tower of Mzark  90.12.11.ess")
# dumpsinglesave(base + "Save 10 - Teerwyn  Windhelm  12.32.40.ess")
##dumpsinglesave(base + "Save 25 Marcus  Whiterun 49.46.41.ess")
##print(arr2fid('78, 77, 160, '))
##print(fid2arr('00060294'))

##dump_analysisfile('Anastasia', base)
##print(gen_flags(50334314))



##ucdata = list(ucdata)
##for n,i in enumerate(ucdata):
##    if n >= 3 and ucdata[n-4:n] == [255,255,127,127]:
##        print(int32(bytes(ucdata[n+4:n+8])))
##        print(float_(bytes(ucdata[n-8:n-4])))


##print(data1[0x14]['data'])
##out = ''
##for i in data1.keys():
##    out += str(i) + '\n\n'
##    out += str(data1[i]['data']) + '\n\n\n'

##with open('output.txt', 'w') as o:
##    o.write(out)
##data2 = main(fname2)
##for i in data1.keys():
##    if i not in data2:
##        removed += 1
##    elif data1[i] != data2[i]:
##        changed += 1
##print('Removed: {}\nChanged: {}'.format(removed,changed))
