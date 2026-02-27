import os, sys, pdb, json, time, logging, tempfile, shutil
import unittest as test
from pathlib import Path
from typing import Mapping

import yaml

from nistoar.testing import *
from nistoar.taxonomy.cache import files

testdir = Path(__file__).parents[0]
basedir = testdir.parents[4]
taxdir = basedir / 'model'
taxfile = taxdir / 'theme-taxonomy.json'

loghdlr = None
rootlog = None
tmpdir  = None
def setUpModule():
    global loghdlr
    global rootlog
    global tmpdir
    tmpdir = tempfile.TemporaryDirectory(prefix="_test_tax.")
    rootlog = logging.getLogger()
    rootlog.setLevel(logging.DEBUG)
    loghdlr = logging.FileHandler(os.path.join(tmpdir.name,"test_tax.log"))
    loghdlr.setLevel(logging.DEBUG)
    loghdlr.setFormatter(logging.Formatter("%(levelname)s: %(name)s: %(message)s"))
    rootlog.addHandler(loghdlr)

def tearDownModule():
    global loghdlr
    global tmpdir
    if loghdlr:
        if rootlog:
            rootlog.removeHandler(loghdlr)
            loghdlr.flush()
            loghdlr.close()
        loghdlr = None
    if tmpdir:
        tmpdir.cleanup()

NIST_THEMES_URI_BASE = "https://data.nist.gov/od/dm/nist-themes/"

class FilesTaxonomyCacheTest(test.TestCase):

    def setUp(self):
        pass

    def test_scan_load(self):
        cache = files.FileTaxonomyCache(taxdir, r"^theme-taxonomy.*")
        self.assertEqual(cache.count(), 3)
        ids = list(cache.ids())
        self.assertTrue(all(d.startswith(NIST_THEMES_URI_BASE) for d in ids))
        self.assertIn(NIST_THEMES_URI_BASE+'v2.0', ids)
        self.assertIn(NIST_THEMES_URI_BASE+'v1.1', ids)
        self.assertIn(NIST_THEMES_URI_BASE+'p1.0', ids)

        self.assertTrue(cache.is_known(NIST_THEMES_URI_BASE+'v2.0'))
        self.assertTrue(cache.is_known(NIST_THEMES_URI_BASE+'v1.1'))
        self.assertTrue(cache.is_known(NIST_THEMES_URI_BASE+'p1.0'))

        info = cache.about(NIST_THEMES_URI_BASE+'v2.0')
        self.assertTrue(isinstance(info, Mapping))
        self.assertIn('location', info)
        self.assertIn('id', info)
        self.assertIn('title', info)
        self.assertIn('version', info)
        self.assertTrue(os.path.isfile(info['location']))

        tax = cache.load_taxonomy(NIST_THEMES_URI_BASE+'v2.0')
        self.assertTrue(isinstance(tax, files.Taxonomy))
        self.assertEqual(tax.id, NIST_THEMES_URI_BASE+'v2.0')
        self.assertTrue(tax.about_term('Bioscience'))

    def test_export(self):
        cache = files.FileTaxonomyCache(taxdir, r"^theme-taxonomy.*")

        outf = Path(tmpdir.name) / "tl.json"
        self.assertTrue(not outf.exists())
        try:
            cache.export_locations(outf)
            self.assertTrue(outf.is_file())
            with open(outf) as fd:
                taxes = json.load(fd)

            self.assertTrue(isinstance(taxes, Mapping))
            self.assertNotIn('baseDirectory', taxes)
            self.assertNotIn('pattern', taxes)
            self.assertEqual(len(taxes.get('taxonomy')), 3)
            locs = [Path(t['location']) for t in taxes['taxonomy']]

            # destination dir is different from location of files, so paths are absolute
            self.assertTrue(all(p.is_absolute() for p in locs))
            self.assertTrue(all(p.is_file() for p in locs))

        finally:
            if outf.exists():
                os.remove(outf)

        outf = Path(tmpdir.name) / "taxonomyLocations.json"
        self.assertTrue(not outf.exists())
        try:
            cache.export_locations(tmpdir.name, "json")
            self.assertTrue(outf.is_file())
            with open(outf) as fd:
                taxes = json.load(fd)

            self.assertTrue(isinstance(taxes, Mapping))
            self.assertNotIn('baseDirectory', taxes)
            self.assertNotIn('pattern', taxes)
            self.assertEqual(len(taxes.get('taxonomy')), 3)
            locs = [Path(t['location']) for t in taxes['taxonomy']]

            # destination dir is different from location of files, so paths are absolute
            self.assertTrue(all(p.is_absolute() for p in locs))
            self.assertTrue(all(p.is_file() for p in locs))

        finally:
            if outf.exists():
                os.remove(outf)

        outf = Path(tmpdir.name) / "taxonomyLocations.yml"
        self.assertTrue(not outf.exists())
        try:
            cache.export_locations(tmpdir.name)
            self.assertTrue(outf.is_file())
            with open(outf) as fd:
                taxes = yaml.safe_load(fd)

            self.assertTrue(isinstance(taxes, Mapping))
            self.assertNotIn('baseDirectory', taxes)
            self.assertNotIn('pattern', taxes)
            self.assertEqual(len(taxes.get('taxonomy')), 3)
            locs = [Path(t['location']) for t in taxes['taxonomy']]

            # destination dir is different from location of files, so paths are absolute
            self.assertTrue(all(p.is_absolute() for p in locs))
            self.assertTrue(all(p.is_file() for p in locs))

            # now try reloading cache from this file
            cache = files.FileTaxonomyCache(outf)
            self.assertEqual(cache.count(), 3)
            id = list(cache.ids())[0]
            tax = cache.load_taxonomy(id)

        finally:
            if outf.exists():
                os.remove(outf)

class MoreExportTest(test.TestCase):

    def setUp(self):
        self.taxdir = Path(tmpdir.name) / "taxons"
        if self.taxdir.is_dir():
            shutil.rmtree(self.taxdir)

        os.mkdir(self.taxdir)
        for f in os.listdir(taxdir):
            if "-taxonomy" in f:
                shutil.copy(taxdir/f, self.taxdir)

    def tearDown(self):
        if self.taxdir.is_dir():
            shutil.rmtree(self.taxdir)

    def test_baseDirectory(self):
        cache = files.FileTaxonomyCache(self.taxdir, r"^.*-taxonomy.*\.json")
        self.assertEqual(cache.count(), 6)

        outf = self.taxdir/"taxonomyLocations.json"
        self.assertTrue(not outf.exists())
        cache.export_locations(self.taxdir, "json", True)
        
        self.assertTrue(outf.is_file())
        with open(outf) as fd:
            taxes = json.load(fd)
        self.assertEqual(taxes.get('baseDirectory'), str(self.taxdir))
        self.assertNotIn('pattern', taxes)
        self.assertEqual(len(taxes.get('taxonomy')), 6)
        locs = [Path(t['location']) for t in taxes['taxonomy']]

        # destination dir is different from location of files, so paths are absolute
        self.assertTrue(all(not p.is_absolute() for p in locs))
        self.assertTrue(all((self.taxdir/p).is_file() for p in locs))

        # now reread the locations file to load the 
        cache = files.FileTaxonomyCache(outf)
        self.assertEqual(cache.count(), 6)
        id = list(cache.ids())[0]
        tax = cache.load_taxonomy(id)


    def test_implied_baseDirectory(self):
        cache = files.FileTaxonomyCache(self.taxdir, r"^.*-taxonomy.*\.json")
        self.assertEqual(cache.count(), 6)

        outf = self.taxdir/"taxonomyLocations.yml"
        self.assertTrue(not outf.exists())
        cache.export_locations(self.taxdir)
        
        
        self.assertTrue(outf.is_file())
        with open(outf) as fd:
            taxes = yaml.safe_load(fd)
        self.assertNotIn('baseDirectory', taxes)
        self.assertNotIn('pattern', taxes)
        self.assertEqual(len(taxes.get('taxonomy')), 6)
        locs = [Path(t['location']) for t in taxes['taxonomy']]

        # destination dir is different from location of files, so paths are absolute
        self.assertTrue(all(not p.is_absolute() for p in locs))
        self.assertTrue(all((self.taxdir/p).is_file() for p in locs))

        # now reread the locations file to load the 
        cache = files.FileTaxonomyCache(outf)
        self.assertEqual(cache.count(), 6)
        id = list(cache.ids())[0]
        tax = cache.load_taxonomy(id)

    

        

if __name__ == '__main__':
    test.main()
