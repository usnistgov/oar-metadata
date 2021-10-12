"""
Some common classes and functions useful across the nistoar namespace
"""
import logging

class SystemInfoMixin(object):
    """
    a mixin for getting information about the current system that a class is 
    a part of.  
    """

    def __init__(self, sysname, sysabbrev, subsname, subsabbrev, version):
        self._sysn = sysname
        self._abbrev = sysabbrev
        self._subsys = subsname
        self._subabbrev = subsabbrev
        self._ver = version

    @property
    def system_name(self):
        return self._sysn

    @property
    def system_abbrev(self):
        return self._abbrev

    @property
    def subsystem_name(self):
        return self._subsys

    @property
    def subsystem_abbrev(self):
        return self._subabbrev

    @property
    def system_version(self):
        return self._ver

    def _getSysLogger(self):
        """
        return the default logger for this subsystem
        """
        out = logging.getLogger(self.system_abbrev)
        if self.subsystem_abbrev:
            out = out.getChild(self.subsystem_abbrev)
        return out


class OARException(Exception):
    """
    a common base class for all OAR-related exceptions
    """

    def __init__(self, message=None, cause=None, sys=None):
        """
        instantiate the exception
        :param str     message:  the description of and reason for the exception
        :param Exception cause:  the intercepted exception that is the underlying cause for this 
                                 exception.  None (default) indicates there is no other underlying 
                                 cause beyond what is provided by the message.
        """
        if not message:
            if cause:
                message = str(cause)
            else:
                message = "Unknown OAR exception occurred"
        self.cause = cause
        self.system = sys
        super(OARException, self).__init__(message)
        
