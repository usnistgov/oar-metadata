"""
Some common classes and functions useful across the nistoar namespace
"""
import logging

class SystemInfoMixin(object):
    """
    an interface for accessing and using information about a particular OAR system a component 
    is a part of.  This class can be used either as a mixin parent class or as the class of 
    an internal class variable.  
    """

    # the currently set global system; see get_global_system() below
    __globalsys = None

    def __init__(self, sysname: str, sysabbrev: str, subsname: str, subsabbrev: str, version: str):
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

    def getSysLogger(self):
        """
        return the default logger for this subsystem
        """
        out = logging.getLogger(self.system_abbrev)
        if self.subsystem_abbrev:
            out = out.getChild(self.subsystem_abbrev)
        return out

    @classmethod
    def get_global_system(cls):
        """
        return the system instance currently set as the global system.  This instance is intended to 
        be set at __main__/script level when the script is intended to operate as part of a single 
        system.  Some class constructors may consult this to determine which system the instance should 
        be considered part of.  If None, no system has been so set.  
        """
        return cls.__globalsys

    def make_global(self):
        """
        register this system instance as the global system.  This method is intended to be called at
        the __main__/script level to indicate that the script is operating as part of this system.  
        There can only be one global system registered, so if this method has been called on any other 
        system object, the previous one is replaced.  
        """
        self.__class__.__globalsys = self

def get_global_system() -> SystemInfoMixin:
    """
    return the SystemInfoMixin instance currently set as the global system.  This is a convenience 
    function for ``SystemInfoMixin.get_global_system()``.
    """
    return SystemInfoMixin.get_global_system()


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
        if not sys:
            sys = SystemInfoMixin.get_global_system()
        self.system = sys
        super(OARException, self).__init__(message)
        
class OARWarning(Warning):
    """
    a common base class for all OAR-related warnings
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
        if not sys:
            sys = SystemInfoMixin.get_global_system()
        self.system = sys
        super(OARException, self).__init__(message)
        
