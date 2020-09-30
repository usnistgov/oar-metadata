"""
module for matching terms from the NIST research topic taxonomy
"""
import os, re, json
from collections import OrderedDict

class ResearchTopicsTaxonomy(object):
    """
    a container and interface to the NIST research topic taxonomy
    """

    def __init__(self, taxjson):
        """
        initialize the instance by wrapping the JSON-encoded taxonomy description
        :param dict taxjson:  the taxonomy data 
        """
        self.data = taxjson
        self.taillu = None
        self.fulllu = None
        self._mklus()

    @classmethod
    def from_file(cls, vocabfile):
        """
        given the taxonomy data description file, create an instance
        """
        if not os.path.exists(vocabfile):
            raise RuntimeError("Unable to find taxonomy file: "+vocabfile)

        with open(vocabfile) as fd:
            data = json.load(fd, object_pairs_hook=OrderedDict)
        return cls(data)

    @classmethod
    def from_schema_dir(cls, schemadir):
        """
        given directory containing the taxonomy data description file, 
        create an instance of the taxonomy class
        """
        return cls.from_file(os.path.join(schemadir, "theme-taxonomy.json"))

    def _mklus(self):
        self.taillu = OrderedDict()
        self.fulllu = OrderedDict()
        for termdef in self.data['vocab']:
            termdef['fullterm'] = self.TaxonomyTerm.make_full_term(termdef)
            self.taillu[termdef['term']] = termdef
            self.fulllu[termdef['fullterm']] = termdef

    _match_ignore = "& / and or".split()
    _ignore_chars = re.compile(r"[()/:]")
    
    def match_theme(self, theme, latest=True):
        """
        given a theme, find its best match to a vocabulary term.  This 
        converts terms that may not be quite exact--e.g. mismatched 
        capitalization, extra words, missing parent terms--to be converted
        to exact taxonomy terms.  It can also convert deprecated terms to 
        their latest counterparts.  
        :param str theme:  the theme value of interest
        :rtype TaxonomyTerm:  the vocabulary terms definition data
        """
        out = None

        # try an exact match
        if theme in self.fulllu:
            out = self.fulllu[theme]
        if theme in self.taillu:
            out = self.taillu[theme]

        if not out:
            # try a near match
            words = [w for w in self._ignore_chars.sub(' ', theme).split()
                       if w not in self._match_ignore]

            # find the theme words in the same order
            patt = r"\b" + r"\b.*\b".join(words) + r"\b"
            matchagainst = (':' in theme and 'fullterm') or 'term'
            matches = [t for t in self.data['vocab']
                         if re.search(patt,
                                      self._ignore_chars.sub(' ', t[matchagainst]),
                                      re.I)]

            # find the best match: pull out the matching words, the match 
            # with the least left is considered the best match    
            min = 20
            best = -1
            for i,m in enumerate(matches):
                stripped = self._ignore_chars.sub(' ', m[matchagainst]).strip()
                for word in words:
                    stripped = re.sub(r'\b'+word+r'\b', '', stripped, flags=re.I)\
                                 .strip()
                stripped = stripped.split() # to look at the number of words
                if len(stripped) < min:
                    min = len(stripped)
                    best = i

            if best >= 0:
                out = matches[best]

        if out and latest and 'deprecatedBy' in out and \
           out['deprecatedBy'] in self.fulllu:
            # replace deprecated term with latest
            out = self.fulllu[out['deprecatedBy']]

        if out:
            out = self.TaxonomyTerm(out, self.data)
        return out

    def themes2topics(self, themes, latest=True, incl_unrec=True):
        """
        Convert the given theme terms to NERDm topic nodes referencing the 
        NIST Research Taxonomy.  The input terms can be approximate matches 
        to the NIST taxonomy--i.e. have missing or misspelled words, 
        incorrect capitalization, or missing parent componets; this function 
        will match them to proper values in the taxonomy
        :param list themes:      an array of theme terms
        :param boolean latest:   if True and a theme matches a deprecated theme,
                                 an attempt is made to 
        :param boolean incl_unrec: if True and a theme cannot be matched to a 
                                 term in the NIST taxonomy, do not include it in 
                                 the output.
        """
        out = []
        for theme in themes:
            term = self.match_theme(theme, latest)
            if term:
                out.append(term.as_topic())
            elif incl_unrec:
                out.append(OrderedDict([("@type", "Concept"), ("tag", theme)]))

        return out


    class TaxonomyTerm(object):
        """
        a vocabulary term from the taxonomy
        """
        @classmethod
        def make_full_term(cls, definition):
            out = definition['term']
            if 'parent' in definition:
                out = "{0}: {1}".format(definition['parent'], out)
            return out

        def __init__(self, definition, taxonomy):
            self.defn = definition
            self.tax = taxonomy

        def __str__(self):
            if 'fullterm' in self.defn:
                return self.defn['fullterm']
            return self.make_full_term(self.defn)

        def as_topic(self):
            """
            return a NERDm topic node for this term
            :rtype dict:  the NERDm topic node
            """
            return OrderedDict([("@type", "Concept"), ("scheme", self.tax['@id']),
                                ("tag", str(self))])

                              
                
            
