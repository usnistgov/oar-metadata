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
                msg = "Unknown Preservation System Error"
        super(PreservationException, self).__init__(msg)
        self.cause = cause

class NERDError(MetadataError):
    """
    an exception indicating an error handling NERDm metadata
    """
    pass

class MergeError(MetadataError):
    """
    an exception indicating an error merging metadata 
    """
    pass
