"""
Exceptions issued by the NERDm utilities
"""
from ..base import OARException

class MetadataError(OARException):
    """
    an exception indicating an error handling metadata
    :param str msg:          the message describing the error that occurred
    :param Exception cause:  the exception that originally caught the error; if None, the 
                               error was discovered by catching an exception
    :param src:              the file containing the errant metadata; if None, no such 
                               file source was involved or is known
    :type src: str or Path
    :param SysInfoMixin sys: the OAR system that generated the error; if None, the system
                               will be discerned
    """
    def __init__(self, msg=None, cause=None, src=None, sys=None):
        if not msg and not cause:
            msg = "Unknown Metadata Error"
        super(MetadataError, self).__init__(msg, cause, sys)
        self.source = src

class PODError(MetadataError):
    """
    an exception indicating an error handling POD metadata
    """
    def __init__(self, msg=None, cause=None, src=None, sys=None):
        if not msg and not cause:
            msg = "Unknown POD metadata error"
        super(PODError, self).__init__(msg, cause, src, sys)
    pass

class NERDError(MetadataError):
    """
    an exception indicating an error handling NERDm metadata
    """
    """
    an exception indicating an error handling POD metadata
    """
    def __init__(self, msg=None, cause=None, src=None, sys=None):
        if not msg and not cause:
            msg = "Unknown NERD metadata error"
        super(PODError, self).__init__(msg, cause, src, sys)
    pass

class NERDTypeError(NERDError):
    """
    an exception indicating that a NERm metadata value is of an invalid or 
    unexpected type.
    """
    def __init__(self, need=None, got=None, property=None, msg=None, cause=None, src=None, sys=None):
        """
        create the exception

        :param            need:  the value type or types that were expected
                                 :type need: str or list/tuple of str
        :param             got:  the type actualy found or given
                                 :type got: str or type
        :param str    property:  the name of the property with the incorrect type
        :param str         msg:  a message that overrides the default based on 
                                 need and got.
        :param Exception cause:  an exception that was a result of this 
                                 problem.
        :param src:              the file containing the errant metadata; if None, no such 
                                 file source was involved or is known
                                 :type src: str or Path
        """
        self.need = need
        self.got = got
        if not msg:
            msg = ""
            if property:
                msg += property + ": "
            msg = "Incorrect NERDm metadata value type"
            if need:
                msg += ": expected "
                if isinstance(need, (list, tuple)):
                    msg += "one of " + str(need)
                else:
                    msg += str(need)
            if got:
                msg += (need and ",") or ":" + " got " + str(got)

        super(NERDTypeError, self).__init__(msg, cause, sys)


class MergeError(MetadataError):
    """
    an exception indicating an error merging metadata 
    """
    pass
