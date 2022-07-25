"""
library for supporting NERDm metadata
"""

from .version import __version__

from .validate import validate as validate_nerdm, ValidationError
from .constants import CORE_SCHEMA_URI, PUB_SCHEMA_URI
from .utils import *


