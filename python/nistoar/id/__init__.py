"""
This module provides for management of persistent identifiers, particularly 
creating (i.e. "minting") them.  

The PDR assigns ARK identifiers to all the resources it manages.
"""
from __future__ import absolute_import
from .version import __version__
from .minter import NIST_ARK_NAAN
from .persist import PDRMinter

