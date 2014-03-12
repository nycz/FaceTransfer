import json
import os
from os.path import join, splitext
import unittest

import extract


class ExtractionTest(unittest.TestCase):

    def test_extract_data(self):
        root = join('testdata', 'test_extract_data')
        for fname in os.listdir(root):
            if splitext(fname)[1] != '.ess':
                continue
            with open(join(root, fname)+'.json') as f:
                cdata = json.loads(f.read())
            plugininfo, fidarray, playerdata, playerflags, required_plugins\
                = extract.extract_data(join(root, fname))
            self.assertEqual(cdata['plugininfo'], plugininfo)
            self.assertEqual(cdata['fidarray'], fidarray)
            self.assertEqual(cdata['required plugins'], required_plugins)
            self.assertEqual(cdata['flags'], playerflags)
            self.assertEqual(cdata['hair color'], playerdata['hair color'])
            self.assertEqual(cdata['skin color'], playerdata['skin color'])
            self.assertEqual(cdata['head texture'], playerdata['head texture'])
            self.assertEqual(cdata['headparts'], playerdata['headparts'])
            self.assertEqual(cdata['unknown1'], playerdata['unknown1'])
            self.assertEqual(cdata['face morph values'], playerdata['face morph values'])
            self.assertEqual(cdata['faceparts'], playerdata['faceparts'])
            if 'female' in cdata:
                self.assertIn('female', playerdata)
                self.assertEqual(cdata['female'], playerdata['female'])

if __name__ == '__main__':
    unittest.main()