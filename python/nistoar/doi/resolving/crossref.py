from .common import DOIInfo, default_doi_resolver
from . import common as _comm

import crossref.restful as xref

class CrossrefDOIInfo(DOIInfo):
    """
    a specialization of DOIInfo for Datacite DOIs.  This specialization knows
    how to retrieve the native DOI metadata.
    """

    def __init__(self, doi, source="Crossref", resolver=default_doi_resolver,
                 logger=None, client_info=None):
        super(CrossrefDOIInfo, self).__init__(doi, source, resolver, logger, client_info)
        if self._client_info:
            self._client_info = xref.Etiquette(*self._client_info)

    @property
    def native(self):
        """
        DOI metadata in the schema specific to the registration agency--in 
        this case, Datacite.
        """
        if self._native is None:
            if self.log and not self.client_info:
                self.log.warn("Crossref client info not set; "+
                              "call nistoar.doi.set_client() to set")

            self._native = xref.Works(etiquette=self.client_info).doi(self.id)

        return self._native

