#!/usr/bin/env python3

from collections import defaultdict
from os.path import basename, join
import pprint
import extract


def readable_bytes(data: bytes) -> str:
    return ' '.join(str(b).zfill(3) for b in data)

falloutformat = """{fname}
flags: {flags}

Flag 1
flag1data: {flag1data}

Flag 6
factionsize: {factionsize}
factions: {factions}

Flag 5
name: {name}

Flag 24
gender: {gender}

Flag 11
flag11unknown1: {flag11unknown1}
headpart1: {headpart1}
unknowncolor: {unknowncolor}
headpart2: {headpart2}
headpartcount: {headpartcount}
headparts: {headparts}
tetitendpresent: {tetitendpresent}
tetitendsize: {tetitendsize}
tetitend: {tetitend}
facesliderssize: {facesliderssize}
facesliders: {facesliders}
faceextrassize: {faceextrassize}
faceextras: {faceextras}

Flag 14
bodyunknowncount: {bodyunknowncount}
bodyunknown: {bodyunknown}
bodysliderthin: {bodysliderthin}
bodyslidermuscular: {bodyslidermuscular}
bodysliderlarge: {bodysliderlarge}
"""

def dump_file(fname, rawplayer, npc, achr):
    with open(fname, 'rb') as f:
        rawdata = f.read()
    game, data = extract.parse_savedata(rawdata)
    cfdata = extract.parse_changeforms(data['changeforms'])
    if rawplayer:
        with open(join('savedumps', basename(fname) + '.rawsavedump'), 'w') as f:
            f.write('{}\n\n{}'.format(cfdata['playerchangeflags'],
                                      readable_bytes(cfdata['playerdata'])))
        return

    player = extract.parse_player(cfdata['playerdata'],
                                  cfdata['playerchangeflags'],
                                  game)
    if npc:
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
    if achr:
        cfdata2 = extract.parse_changeforms(data['changeforms'], refidnr=0x14)
        with open(join('savedumps', basename(fname) + '.ACHRsavedump'), 'w') as f:
            flags = cfdata2['playerchangeflags']
            f.write('{}\n\n{}'.format(flags, readable_bytes(cfdata2['playerdata'])))

def dry_transfer(sourcefname, targetfname):
    with open(sourcefname, 'rb') as f:
        sourcerawdata = f.read()
    with open(targetfname, 'rb') as f:
        targetrawdata = f.read()
    sourcegame, sourcedata = extract.parse_savedata(sourcerawdata)
    targetgame, targetdata = extract.parse_savedata(targetrawdata)
    # Get the player data from the source save
    sourcecfdata = extract.parse_changeforms(sourcedata['changeforms'])
    sourceplayer = extract.parse_player(sourcecfdata['playerdata'],
                                        sourcecfdata['playerchangeflags'],
                                        sourcegame)
    # Get the data from target save
    targetcfdata = extract.parse_changeforms(targetdata['changeforms'])
    targetplayer = extract.parse_player(targetcfdata['playerdata'],
                                        targetcfdata['playerchangeflags'],
                                        targetgame)
    # Merge players, return target player with source's face
    newplayer, newflags = extract.merge_player(
        sourceplayer, sourcecfdata['playerchangeflags'],
        targetplayer, targetcfdata['playerchangeflags'],
        sourcegame
    )
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(newplayer)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('files', nargs='+')
    parser.add_argument('-n', '--npc', action='store_true')
    parser.add_argument('-a', '--achr', action='store_true')
    parser.add_argument('-p', '--raw-player', action='store_true')
    parser.add_argument('-d', '--dry-transfer', action='store_true')
    args = parser.parse_args()
    if args.dry_transfer:
        dry_transfer(args.files[0], args.files[1])
    else:
        for f in args.files:
            dump_file(f, args.raw_player, args.npc, args.achr)

