from os.path import isfile
from os import rename
import extract

def get_ui_data(fname):
    """
    Return data useful for the UI to display, such as name, file info etc.
    """
    with open(fname, 'rb') as f:
        rawdata = f.read()
    game, data = extract.parse_savedata(rawdata)
    out = {}
    out['save number'] = data['savenumber']
    out['name'] = data['playername']
    out['level'] = data['playerlevel']
    out['location'] = data['playerlocation']
    out['race'] = data['playerraceeditorid']
    out['gender'] = data['playersex']
    out['playing time'] = data['gamedate']
    out['screenshot'] = (data['shotwidth'], data['shotheight'], data['screenshotdata'])
    return out, game


def transfer_face(sourcefname: str, targetfname: str):
    """
    Copy facial data from one save file to another. This function should be
    the main entry point for the UI.
    """
    with open(sourcefname, 'rb') as f:
        sourcerawdata = f.read()
    with open(targetfname, 'rb') as f:
        targetrawdata = f.read()
    sourcegame, sourcedata = extract.parse_savedata(sourcerawdata)
    targetgame, targetdata = extract.parse_savedata(targetrawdata)
    if sourcegame != targetgame:
        raise Exception('Saves are not from the same game!')
    if sourcedata['playersex'] != targetdata['playersex']:
        raise Exception('Characters must have the same gender!')
    if sourcedata['playerraceeditorid'] != targetdata['playerraceeditorid']:
        raise Exception('Characters must be the same race!')
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
    # Encode and put the new face and flags in the target changeform data
    targetcfdata['playerdata'] = extract.encode_player(newplayer, sourcegame)
    targetcfdata['playerchangeflags'] = newflags
    # Encode the changeform data and put it in the target main data
    targetdata['changeforms'] = extract.encode_changeforms(targetcfdata)
    # Then encode the whole file
    newrawdata = extract.encode_savedata(targetdata)
    # Write to disk
    i = 0
    while isfile(targetfname+'.facebak'+str(i)):
        i += 1
    rename(targetfname, targetfname+'.facebak'+str(i))
    with open(targetfname, 'wb') as f:
        f.write(newrawdata)
    return True
