"""
Exceptions issued by the NERDm utilities
"""

class MetadataError(Exception):
    """
    an exception indicating an error handling metadata
    """
    def __init__(self, msg=None, cause=None):
        if not msg:
            if cause:
                msg = str(cause)
            else:
                msg = "Unknown Metadata System Error"
        super(MetadataError, self).__init__(msg)
        self.cause = cause

class NERDError(MetadataError):
    """
    an exception indicating an error handling NERDm metadata
    """
    pass

class NERDTypeError(MetadataError):
    """
    an exception indicating that a NERm metadata value is of an invalid or 
    unexpected type.
    """
    def __init__(self, need=None, got=None, property=None, msg=None, cause=None):
        """
        create the exception

        :param need str or list/tuple of str:  the value type or types 
                             that were expected
        :param got  str or type:  the type actualy found or given
        :param property str:  the name of the property with the incorrect type
        :param msg  str:  a message that overrides the default based on 
                             need and got.
        :param cause Exception:  an exception that was a result of this 
                             problem.
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

        super(NERDTypeError, self).__init__(msg, cause)


class MergeError(MetadataError):
    """
    an exception indicating an error merging metadata 
    """
    pass
