#!/usr/bin/env python3
#
import os
from pathlib import Path
import nistoar.taxonomy as tax
schemadir = os.environ.get('SCHEMA_DIR')
if schemadir:
    schemadir = Path(schemadir)
cache = tax.FileTaxonomyCache(schemadir/'taxonomyLocations-by-patt.yml')
print(f"Registering {cache.count()} taxonomies")
cache.export_locations(schemadir)
