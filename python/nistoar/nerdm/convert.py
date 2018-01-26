"""
Classes and functions for converting from and to the NERDm schema
"""
import os, json
from .. import jq

class PODds2Res(object):
    """
    a transformation engine for converting POD Dataset records to NERDm
    resource records.
    """

    def __init__(self, jqlibdir):
        """
        create the converter

        :param jqlibdir str:   path to the directory containing the nerdm jq
                               modules
        """
        self.jqt = jq.Jq('nerdm::podds2resource', jqlibdir, ["pod2nerdm:nerdm"])

    def convert(self, podds, id):
        """
        convert JSON-encoded data to a resource object

        :param podds str:   a string containing the JSON-formatted input POD 
                            Dataset record
        :param id str:      The identifier to assign to the output NERDm resource
        """
        return self.jqt.transform(podds, {"id": id})

    def convert_data(self, podds, id):
        """
        convert parsed POD record data to a resource object

        :param podds str:   a string containing the JSON-formatted input POD 
                            Dataset record
        :param id str:      The identifier to assign to the output NERDm resource
        """
        return self.jqt.transform(json.dumps(podds), {"id": id})

    def convert_file(self, poddsfile, id):
        """
        convert parsed POD record data to a resource object

        :param podds str:   a string containing the JSON-formatted input POD 
                            Dataset record
        :param id str:      The identifier to assign to the output NERDm resource
        """
        return self.jqt.transform_file(poddsfile, {"id": id})

class ComponentCounter(object):
    """
    a class for calculating inventories using the jq conversion macros
    """

    def __init__(self, jqlibdir):
        """
        create the counter

        :param jqlibdir str:   path to the directory containing the nerdm jq
                               modules
        """
        self._modules = ["pod2nerdm:nerdm"]
        self._jqlibdir = jqlibdir

        self._inv_jqt = self._make_jqt('nerdm::inventory_components')
                              
    def _make_jqt(self, macro):
        return jq.Jq(macro, self._jqlibdir, self._modules)

    def inventory(self, components):
        """
        return an inventory NERDm property value that reflects the make-up of 
        the given array of component data.
        """
        datastr = json.dumps(components)
        return self._inv_jqt.transform(datastr)

    def inventory_collection(self, components, collpath):
        """
        return an inventory for components within a given subcollection.

        :param components list:  a list of components that includes those within
                                 the requested subcollection
        :param collpath    str:  the filepath for the desired subcollection to 
                                 inventory
        """
        macro = 'nerdm::inventory_collection("{0}")'.format(collpath)
        jqt = self._make_jqt(macro)
        datastr = json.dumps(components)
        return jqt.transform(datastr)

    def inventory_by_type(self, components, collpath):
        """
        return an inventory broken down by type within a given subcollection.

        :param components list:  a list of components that includes those within
                                 the requested subcollection
        :param collpath    str:  the filepath for the desired subcollection to 
                                 inventory
        """
        macro = 'nerdm::inventory_by_type("{0}")'.format(collpath)
        jqt = self._make_jqt(macro)
        datastr = json.dumps(components)
        return jqt.transform(datastr)

class HierarchyBuilder(object):
    """
    a class for calculating data hierarchies using the jq conversion macros
    """

    def __init__(self, jqlibdir):
        """
        create the builder.

        :param jqlibdir str:   path to the directory containing the nerdm jq
                               modules
        """
        self._modules = ["pod2nerdm:nerdm"]
        self._jqlibdir = jqlibdir

        self._hier_jqt = self._make_jqt('nerdm::hierarchy("")')
                              
    def _make_jqt(self, macro):
        return jq.Jq(macro, self._jqlibdir, self._modules)

    def build_hierarchy(self, components):
        """
        return an array representing the data hierarchy for a given set of 
        components.

        This is implemented via the appropriate jq translation macros.  
        """
        datastr = json.dumps(components)
        return self._hier_jqt.transform(datastr)


        
    
    
