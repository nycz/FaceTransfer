Skyrim Face Transfer Workflow
=============================

Written top-down, that is with the focus on what the users want to do,
and how that is to be done using what functions et cetera.


Glossary~ish
------------
    source              = file with the face that is to be saved
    target              = file with the body that is to be used
    non-vanilla formID  = the first two bits in the first byte is 0


Datatypes or something (pseudocode)
-----------------------------------

### SaveData
    header, screenshot, formversion, plugininfo, flt, gdt1, gdt2, preplayer, player, postplayer, gdt3, formidarray, ut2, ut3
This is where the whole file is represented. This datatype must contain
EVERYTHING to create a valid .ess file.  All parts except screenshot and
player (and possibly plugininfo) are normal bytestrings/charlists.

### Screenshot
    width, height, data

### Player
    flags, lenlen, len1, len2, data(, entrylen)
This datatype must contain EVERYTHING to create a valid ChangeForm
entry for the player.

### FaceData
    race, haircolor, skincolor, headtexture, headparts, facegen, female, flags
TODO: non-vanilla formids and related into must be bundled in some way!


Transfer a face
---------------

1. Load the source file
    - Read the whole file
    - Extract PluginInfo
    - Extract FormIDArray
    - Extract the facedata from the player
    - Go through all 3-byte-FormIDs
        - If it is non-vanilla:
        - Find its real formID in formidarray
        - Find THAT formid's plugin in the plugininfo table
        - Bundle the real formid and it's plugin with the facedata
    - Return facedata

2. Load the target file
    - Read the whole file
    - Cut it up in parts (See SaveData)
        - Cut up ChangeForms in the player's entry and the parts before and after.

3. Update the target's SaveData
    - Update PluginInfo with new plugins from source FaceData
        - Return places for each plugin,
    - Update formID array with new formids from source FaceData
        - That includes the updated position of resp. formid's plugin, using the
          return value from the PluginInfo-update function (the above)
        - Return the new formIDs' indexes
    - Update target player's facedata


Get face info for the GUI
-------------------------

1. Parse the Header
    - Return save number, name, level, location, playing time, race
2. Extract Screenshot
3. Find and parse the Player
    - Return gender




Changed sizes affect what
=========================

Plugin Info
-----------
globalDataTable1Offset
globalDataTable2Offset
changeFormsOffset
globalDataTable3Offset
formIDArrayCountOffset
unknownTable3Offset

changeForms
-----------
globalDataTable3Offset
formIDArrayCountOffset
unknownTable3Offset

formIDArray
-----------
unknownTable3Offset