#!/usr/bin/env python3

from collections import defaultdict
from os.path import basename, join

import extract


def readable_bytes(data: bytes) -> str:
    return ' '.join(str(b).zfill(3) for b in data)

falloutformat = """{fname}
{flags}

Flag 1
{flag1data}

Flag 6
{factionsize}
{factions}

Flag 5
{name}

Flag 24
{gender}

Flag 11
{flag11unknown1}
{headpart1}
{unknowncolor}
{headpart2}
{headpartcount}
{headparts}
{flag11unknown2}
{tetitendsize}
{tetitend}
{facesliderssize}
{facesliders}
{faceextrassize}
{faceextras}

Flag 14
{bodyunknowncount}
{bodyunknown}
{bodysliderthin}
{bodyslidermuscular}
{bodysliderlarge}
"""

def dump_file(fname):
    with open(fname, 'rb') as f:
        rawdata = f.read()
    game, data = extract.parse_savedata(rawdata)
    cfdata = extract.parse_changeforms(data['changeforms'])
    player = extract.parse_player(cfdata['playerdata'],
                                  cfdata['playerchangeflags'],
                                  game)
    out = ''
    if game == 'fallout4':
        keys = defaultdict(str)
        keys['fname'] = fname
        keys['flags'] = cfdata['playerchangeflags']
        keys.update({k:(readable_bytes(v) if isinstance(v, bytes) else v)
                     for k,v in player.items()})
        out = falloutformat.format_map(keys)
    with open(join('savedumps', basename(fname) + '.savedump'), 'w') as f:
        f.write(out)

    cfdata2 = extract.parse_changeforms(data['changeforms'], refidnr=0x14)
    with open(join('savedumps', basename(fname) + '.ACHRsavedump'), 'w') as f:
        flags = cfdata2['playerchangeflags']
        f.write('{}\n\n{}'.format(flags, readable_bytes(cfdata2['playerdata'])))

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('files', nargs='+')
    args = parser.parse_args()
    for f in args.files:
        dump_file(f)

