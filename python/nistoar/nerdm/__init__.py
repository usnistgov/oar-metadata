"""
library for supporting NERDm metadata
"""
from __future__ import absolute_import
from .version import __version__

from .validate import validate as validate_nerdm
from .constants import CORE_SCHEMA_URI, PUB_SCHEMA_URI

