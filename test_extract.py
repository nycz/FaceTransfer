import os
import os.path
import unittest

import extract


class ExtractionTest(unittest.TestCase):

    def test_uint8(self):
        val = 8
        encval = extract.encode_uint8(val)
        l, decval = extract.uint8(0, encval)
        self.assertEqual(val, decval)
        self.assertEqual(l, len(encval))

    def test_uint16(self):
        val = 2000
        encval = extract.encode_uint16(val)
        l, decval = extract.uint16(0, encval)
        self.assertEqual(val, decval)
        self.assertEqual(l, len(encval))

    def test_uint32(self):
        val = 70000
        encval = extract.encode_uint32(val)
        l, decval = extract.uint32(0, encval)
        self.assertEqual(val, decval)
        self.assertEqual(l, len(encval))

    def test_float32(self):
        val = b'0010'
        encval = extract.encode_float32(val)
        l, decval = extract.float32(0, encval)
        self.assertEqual(val, decval)
        self.assertEqual(l, len(encval))

    def test_vsvals(self):
        for v in range(0, 4194304, 1000):
            encval = extract.encode_vsval(v)
            l, decval = extract.vsval(0, encval)
            self.assertEqual(v, decval)
            self.assertEqual(l, len(encval))

    def test_wstring(self):
        val = 'hahablörp'
        encval = extract.encode_wstring(val)
        l, decval = extract.wstring(0, encval)
        self.assertEqual(val, decval)
        self.assertEqual(l, len(encval))

    def test_bytes(self):
        val = b'atn3g2g9'
        encval = extract.encode_bytes(val)
        l, decval = extract.bytes_(0, encval, length=8)
        self.assertEqual(val, decval)
        self.assertEqual(l, len(encval))
        l2, decval2 = extract.bytes_(0, encval, end=8)
        self.assertEqual(val, decval2)
        self.assertEqual(l2, len(encval))

    def test_formids(self):
        val = b'atn3g2g9'
        encval = extract.encode_formids(val)
        l, decval = extract.formids(0, encval, num=2)
        self.assertEqual(val, decval)
        self.assertEqual(l, len(encval))

    def test_refids(self):
        val = b't23ht9aaa'
        encval = extract.encode_refids(val)
        l, decval = extract.refids(0, encval, num=3)
        self.assertEqual(val, decval)
        self.assertEqual(l, len(encval))

    def test_screenshot(self):
        val = b'x' * 10*10*3
        encval = extract.encode_screenshot(val)
        l, decval = extract.screenshot(0, encval, width=10, height=10, colorlength=3)
        self.assertEqual(val, decval)
        self.assertEqual(l, len(encval))
        val2 = b'x' * 10*10*4
        encval2 = extract.encode_screenshot(val2)
        l2, decval2 = extract.screenshot(0, encval2, width=10, height=10, colorlength=4)
        self.assertEqual(val2, decval2)
        self.assertEqual(l2, len(encval2))

    def test_flags(self):
        val = {1,2,6,23,25}
        encval = extract.encode_flags(val)
        decval = extract.flags(0, encval)
        self.assertEqual(val, decval)
        self.assertEqual(4, len(encval))

    def decode_and_encode(self, root):
        for path, _, fnames in os.walk(root):
            for fname in fnames:
                with open(os.path.join(path, fname), 'rb') as f:
                    rawdata = f.read()
                _, data = extract.parse_savedata(rawdata)
                rawdata2 = extract.encode_savedata(data)
                self.assertEqual(rawdata, rawdata2)

    def test_decode_and_encode_skyrim(self):
        self.decode_and_encode('skyrimsaves')

    def test_decode_and_encode_fallout4(self):
        self.decode_and_encode('fallout4saves')

    def decode_and_encode_changeforms(self, root):
        for path, _, fnames in os.walk(root):
            for fname in fnames:
                with open(os.path.join(path, fname), 'rb') as f:
                    rawdata = f.read()
                _, data = extract.parse_savedata(rawdata)
                rawcf1 = data['changeforms']
                cf = extract.parse_changeforms(rawcf1)
                rawcf2 = extract.encode_changeforms(cf)
                self.assertEqual(rawcf1, rawcf2)

    def test_decode_and_encode_changeforms_skyrim(self):
        self.decode_and_encode_changeforms('skyrimsaves')

    def test_decode_and_encode_changeforms_fallout4(self):
        self.decode_and_encode_changeforms('fallout4saves')

    def decode_and_encode_player(self, root):
        for path, _, fnames in os.walk(root):
            for fname in fnames:
                with open(os.path.join(path, fname), 'rb') as f:
                    rawdata = f.read()
                game, data = extract.parse_savedata(rawdata)
                cf = extract.parse_changeforms(data['changeforms'])
                rawplayer1 = cf['playerdata']
                player = extract.parse_player(rawplayer1, cf['playerchangeflags'], game)
                rawplayer2 = extract.encode_player(player, game)
                self.assertEqual(rawplayer1, rawplayer2)

    def test_decode_and_encode_player_skyrim(self):
        self.decode_and_encode_player('skyrimsaves')

    def test_decode_and_encode_player_fallout4(self):
        self.decode_and_encode_player('fallout4saves')

    def merge_player_no_change(self, root):
        for path, _, fnames in os.walk(root):
            for fname in fnames:
                with open(os.path.join(path, fname), 'rb') as f:
                    rawdata = f.read()
                game, data = extract.parse_savedata(rawdata)
                cf = extract.parse_changeforms(data['changeforms'])
                rawplayer1 = cf['playerdata']
                playera = extract.parse_player(rawplayer1, cf['playerchangeflags'], game)
                playerb = extract.parse_player(rawplayer1, cf['playerchangeflags'], game)
                mergedplayer, newflags = extract.merge_player(
                    playera, cf['playerchangeflags'],
                    playerb, cf['playerchangeflags'],
                    game
                )
                rawplayer2 = extract.encode_player(mergedplayer, game)
                self.assertEqual(rawplayer1, rawplayer2)

    def test_merge_player_no_change_fallout4(self):
        self.merge_player_no_change('fallout4saves')

    def merge_player_and_revert(self, fnames):
        """
        Apply the source's face onto the target file and then revert.
        The target should be identical before and after.
        """
        for fname1, fname2 in fnames:
            with open(fname1, 'rb') as f:
                rawsourcedata = f.read()
            with open(fname2, 'rb') as f:
                rawtargetdata = f.read()
            # First get the source for the face
            sourcegame, sourcedata = extract.parse_savedata(rawsourcedata)
            sourcecf = extract.parse_changeforms(sourcedata['changeforms'])
            rawsourceplayer = sourcecf['playerdata']
            sourceplayer = extract.parse_player(rawsourceplayer,
                                                sourcecf['playerchangeflags'],
                                                sourcegame)
            # Then get the target data
            targetgame, targetdata = extract.parse_savedata(rawtargetdata)
            targetcf = extract.parse_changeforms(targetdata['changeforms'])
            rawtargetplayer = targetcf['playerdata']
            targetplayer = extract.parse_player(rawtargetplayer,
                                                targetcf['playerchangeflags'],
                                                targetgame)
            # Merge the source and target
            mergedplayer, mergedflags = extract.merge_player(
                sourceplayer, sourcecf['playerchangeflags'],
                targetplayer, targetcf['playerchangeflags'],
                targetgame
            )
            # Then get a new copy of the target, just to be sure
            target2game, target2data = extract.parse_savedata(rawtargetdata)
            rawtarget2cf = target2data['changeforms']
            target2cf = extract.parse_changeforms(rawtarget2cf)
            rawtarget2player = target2cf['playerdata']
            target2player = extract.parse_player(rawtarget2player,
                                                target2cf['playerchangeflags'],
                                                target2game)
            # Revert the face, aka put the newly read target face
            # onto the old target's data (which atm has source's face)
            revertedplayer, revertedflags = extract.merge_player(
                target2player, target2cf['playerchangeflags'],
                targetplayer, targetcf['playerchangeflags'],
                targetgame
            )
            # Encode the target again and compare
            rawrevertedplayer = extract.encode_player(revertedplayer, targetgame)
            self.assertEqual(rawtargetplayer, rawrevertedplayer)
            # Encode the changeforms and compare
            targetcf['playerdata'] = rawrevertedplayer
            targetcf['playerchangeflags'] = revertedflags
            rawrevertedcf = extract.encode_changeforms(targetcf)
            self.assertEqual(rawtarget2cf, rawrevertedcf)
            # Encode the whole file and compare
            targetdata['changeforms'] = rawrevertedcf
            rawreverteddata = extract.encode_savedata(targetdata)
            self.assertEqual(rawtargetdata, rawreverteddata)

    def test_merge_player_and_revert_fallout4(self):
        fnames = [
            (os.path.join('fallout4saves', 'mergetests', 'pair1a.fos'),
             os.path.join('fallout4saves', 'mergetests', 'pair1b.fos')),
            (os.path.join('fallout4saves', 'mergetests', 'pair2a.fos'),
             os.path.join('fallout4saves', 'mergetests', 'pair2b.fos')),
        ]
        self.merge_player_and_revert(fnames)




if __name__ == '__main__':
    unittest.main()
