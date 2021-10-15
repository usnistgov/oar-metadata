"""
Provide functionality for the Resource Metadata Manager
"""
import os
from abc import ABCMeta, abstractmethod, abstractproperty

from .version import __version__
from ..base import SystemInfoMixin

__all__ = [ 'RMMSystem' ]

_RMMSYSNAME = "Resource Metadata Manager"
_RMMSYSABBREV = "RMM"

class RMMSystem(SystemInfoMixin):
    """
    a mixin providing static information about the RMM system.  

    In addition to providing system information, one can determine if a class 
    instance--namely, an Exception--is part of a particular system by calling 
    `isinstance(inst, RMMSystem)`.
    """
    def __init__(self):
        super(RMMSystem, self).__init__(_RMMSYSNAME, _RMMSYSABBREV, "", "", __version__)

system = RMMSystem()
