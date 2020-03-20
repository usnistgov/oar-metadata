# jq conversion library from NIST-PDL-POD to NERDm schemas
#
# To convert a single POD Dataset document, execute the following:
#
#   jq -L $JQLIB --arg id ID \
#      'import "pod2nerdm" as nerdm; .|nerdm::podds2resource' DSFILE
#
# Here, JQLIB is the directory containing this library, ID is the identifier
# that should be assigned for that record, and DSFILE is a file containing a
# POD Dataset object.
#
# To convert the full PDL catalog into an array of NERDm records, execute:
#
#   jq -L $JQLIB --argjson id null \
#      'import "pod2nerdm" as nerdm; .|nerdm::podcat2resources' CATFILE
#      
# Here, CATFILE is the POD catalog file.  (In this example, the output records
# are all given a null identifier.)

include "urldecode";

# the base NERDm JSON schema namespace
#
def nerdm_schema:  "https://data.nist.gov/od/dm/nerdm-schema/v0.2#";

# the base NERDm JSON schema namespace
#
def nerdm_pub_schema:  "https://data.nist.gov/od/dm/nerdm-schema/pub/v0.2#";

# the NERDm context location
#
def nerdm_context: "https://data.nist.gov/od/dm/nerdm-pub-context.jsonld";

# where the Datacite Document Reference types are defined
#
def dciteRefType: nerdm_schema + "/definitions/DCiteReference";

# the resource identifier provided on the command line
#
def resid:  if $id then $id else null end;

# extract the path component from a URI
#
# Input: string
# Output: string
def urlpath:
    sub("^\\w+:(//\\w+\\.\\w+(\\.\\w+)*(:\\d+)?)?"; "")
;

# trim whitespace from the beginning of a string
#
# Input: string
# Output: string
#
def ltrimsp:
    sub("^\\s+"; "")
;

# trim whitespace from the end of a string
#
# Input: string
# Output: string
#
def rtrimsp:
    sub("\\s+$"; "")
;

# trim whitespace from both ends of a string
#
# Input: string
# Output: string
#
def trimsp:
    ltrimsp | rtrimsp
;

# given a string that looks like a file path, return the path to the
# file's parent directory
#
# Input: string
# Output: string
#
def dirname:
    sub("/$";"") | 
    if contains("/") then
        sub("/[^/]+$"; "")
    else
        ""
    end
;

# given a string that looks like a file path, return the unqualified file
# name.
#
# Input: string
# Output: string
#
def basename:
    sub("/$";"") | 
    if contains("/") then
        sub("^.*/"; "")
    else
        .
    end
;

# remove the filename extension from the input
#
# Input: string
# Output: string
#
def remove_extension:
    if test("\\w\\.") then sub("\\.[^\\.]*$"; "") else . end
;

# assuming an input file name or path return the filename extension or
# an empty string if none exists
#
# Input: string
# Output: string
#
def extension:
    if test("\\w\\.") then sub("^.*\\."; "") else "" end
;

# filter an array of strings, retaining only those that are not in another
# given input array
#
# Input: array of strings
# Output: array of strings
# exclude: array of strings to remove from input array
#
def remove_elements(exclude):
    map(. as $el | select( (exclude | index($el)) == null ))
;

# given a list of filepaths, return a unique array of ancestor collection
# filepaths
#
# Input: array of strings
# Output: array of strings
#
def ansc_coll_paths:
    map(dirname) | map([while(length > 0; dirname)]) |
    reduce .[] as $ary ([]; .+$ary) | unique
;

# conversion for a POD-to-NERDm reference node
#
# Input: a string containing the reference URL
# Output: a DCiteDocumentReference object
#
def cvtref:  {
    "@type": ["deo:BibliographicReference"],
    "@id": ("#ref:" + (. | urlpath | sub("^/"; ""))),
    "refType": "IsReferencedBy",
    "location": .,
    "_extensionSchemas": [ dciteRefType ]
};

# create a relative identifier for a component based on its metadata
#
# Input: the component node
# Output: str, the relative identifier
# prefix: a prefix to insert
#
def componentID(prefix):
    prefix + 
    (if .filepath then .filepath else
        if .accessURL then (.accessURL | urlpath | sub("^/doi:"; "/")) else
           if .downloadURL then (.downloadURL | urlpath) else
               null
           end
        end
     end | sub("^/"; ""))
;

# convert a downloadURL into a filepath value.  This will recognize special
# URL form corresponding to NIST's S3 buckets and the data distribution service
#
# Input:  URL string
# Output: string, representing a filepath to assume
#
def filepath:
    if test("https?://s3.amazonaws.com/nist-srd/\\w+/") then
       sub("https?://s3.amazonaws.com/nist-srd/\\w+/"; "")
    elif test("https?://s3.amazonaws.com/nist-\\w+/\\w+/") then
       sub("https?://s3.amazonaws.com/nist-\\w+/\\w+/"; "")
    elif test("https?://opendata.nist.gov/\\w+/") then
       sub("https?://opendata.nist.gov/\\w+/"; "")
    elif test("https?://[\\w\\.:]+/od/ds/") then
       sub("https?://[\\w\\.:]+/od/ds/"; "") |
       if test("ark:/\\w+/") then
          sub("ark:/\\w+/"; "")
       else . end |
       sub("^[\\w+-]+/"; "") 
    else
       sub(".*/"; "")
    end | url_decode_plus
;

# conversion for a POD-to-NERDm distribution node.  A distribution with a
# downloadURL gets converted to a DataFile component
#
# Input: a Distribution object
# Output: a Component object with a DataFile type given as @type
#
def dist2download:
    .["filepath"] = ( .downloadURL | filepath ) |
    .["@type"] = [ "nrdp:DataFile", "nrdp:DownloadableFile", "dcat:Distribution" ] |
    .["@id"] = (. | componentID("cmps/")) |
    .["_extensionSchemas"] = [ "https://data.nist.gov/od/dm/nerdm-schema/pub/v0.2#/definitions/DataFile" ] |
    if .format then .format = { description: .format } else . end
;

# conversion for a POD-to-NERDm distribution node.  A distribution with a
# downloadURL and a .sha256 extension gets converted to a ChecksumFile component
#
# Input: a Distribution object
# Output: a Component object with a ChecksumFile type given as @type
#
def dist2checksum:
    .["filepath"] = ( .downloadURL | filepath ) |
    .["@type"] = [ "nrdp:ChecksumFile", "nrdp:DownloadableFile", "dcat:Distribution" ] |
    .["@id"] = (. | componentID("cmps/")) |
    .["_extensionSchemas"] = [ "https://data.nist.gov/od/dm/nerdm-schema/pub/v0.2#/definitions/ChecksumFile" ] |
    .["mediaType"] = "text/plain" |
    .["algorithm"] = { "@type": "Thing", tag: (.filepath|extension) } |
    if .description then . else .["description"] = "SHA-256 checksum value for "+(.filepath|basename|remove_extension) end | 
    if .format then .format = { description: .format } else . end
;

# conversion for a POD-to-NERDm distribution node.  A distribution gets converted
# to a Hidden component that is not intended for external use.  (Such nodes
# exist to preserve information for conversion back into POD.)
#
# Input: a Distribution object
# Output: a Component object with an Hidden type given as @type
#
def dist2hidden:
    (if (.accessURL | test("doi.org")) then "#doi:" else "#hdn:" end) as $pfx |
    .["@type"] = [ "nrd:Hidden", "dcat:Distribution" ] |
    .["@id"] = (. | componentID($pfx))
;

# conversion for a POD-to-NERDm distribution node.  A distribution gets converted
# to an Inaccessible component.  This is for distributions that have neither an
# accessURL nor a downloadURL.  
#
# Input: a Distribution object
# Output: a Component object with an Inaccessible type given as @type
#
def dist2inaccess:
    .["@type"] = [ "nrd:Inaccessible", "dcat:Distribution" ]
;

# conversion for a POD-to-NERDm distribution node.  A distribution gets converted
# to a generic AccessPage component.  
#
# Input: a Distribution object
# Output: a Component object with an AccessPage type given as @type
#
def dist2accesspage:
    .["@type"] = [ "nrdp:AccessPage", "dcat:Distribution" ] |
    .["@id"] = (. | componentID("#")) |
    .["_extensionSchemas"] = [ "https://data.nist.gov/od/dm/nerdm-schema/pub/v0.2#/definitions/AccessPage" ] |
    if .format then .format = { description: .format } else . end
;

# conversion for a POD-to-NERDm distribution node.  A distribution gets converted
# to a component of particular types depending on the input data.  See other
# dist2* macros
#
# Input: a Distribution object
# Output: a Component object with the detected types given in @type
#
def dist2comp: 
    if .downloadURL then
        if (.downloadURL | endswith(".sha256")) then
            dist2checksum
        else
            dist2download
        end
    else if .accessURL then
        if (.accessURL | test("doi.org")) then
          dist2hidden
        else
          dist2accesspage
        end
      else
        dist2inaccess
      end
    end
;

# return the DOI stored in the accessURL, if it exists.  null is returned, if
# none is found.
#
# Input: a Distribution object
# Output:  string: A DOI in in the form of "doi:..."
#
def doiFromDist:
    (map(select(.accessURL)| .accessURL | scan("https?://.*doi\\.org/.*")) | .[0]) as $auri |
    if $auri then ($auri | sub("https?://.*doi.org/(doi:)?"; "doi:")) else null end
;

# return a unique list of the @type values from all objects in an array
#
# Input: Array of objects with @type properties
# Output:  Array of strings
#
def obj_types:
    map(.["@type"]) | flatten | unique
;

# select components that appear (deeply) below a subcollection in a hierarchy.
# This is entirely based on the filepath value (not @types)
#
# Input: array of components
# Output: (reduced) array of components
# within: a filepath to a subcollection
#
def select_comp_within(within):
    (if (within|length) == 0 then "" else within+"/" end) as $within |
    map( if .filepath then
            select(.filepath | startswith($within))
         else
            select((within|length) == 0)
         end
    )
;

# select the direct children of a particular subcollection in a hierarchy
# This is entirely based on the filepath value (not @types)
#
# Input: array of components
# Output: (reduced) array of components
# within: a filepath to a subcollection
#
def select_comp_children(within):
    (if (within|length) == 0 then "" else within+"/" end) as $within |
    map( if .filepath then
            select(.filepath | test("^"+$within+"[^/]+/?$"))
         else
            select((within|length) == 0)
         end
    )
;

# select objects that are of specified type
#
# Input: array of objects
# Output: (reduced) array of objects
# type:  a value to match against @type
#
def select_obj_type(type):
    map(select(.["@type"]|contains([type])))
;

# select components that are of specified type below a subcollection in the
# hierarchy.  
#
# Input: array of objects
# Output: (reduced) array of objects
# type:  a value to match against @type
# within: a filepath to a subcollection
#
def select_comp_type(type; within):
    select_obj_type(type) | select_comp_within(within)
;

# create a default Subcollection component for a given filepath
#
# Input: filepath string
# Output: Component
#
def create_subcoll_for:
    {
        "@id": ("cmps/" + .),
        "@type": [ "nrdp:Subcollection" ],
        filepath: .,
        "_extensionSchemas": [ nerdm_pub_schema + "/definitions/Subcollection" ]
    }
;

# create Subcollection components for the filepaths found a given array of
# components and insert them into the beginning of that array.
#
# Input: array of components
# Output: (expanded) array of components
#
def insert_subcoll_comps:
    (select_comp_type("nrdp:Subcollection";"") |
     map(select(.filepath)|.filepath)) as $subcolls |
    (map(select(.filepath)|.filepath) | ansc_coll_paths |
     remove_elements($subcolls) | map(create_subcoll_for)) + .
;

# create an array of TypeInventories summarizing the input set of Components
#
# Input: an array of Components
# Output: an array of TypeInventory objects
# within: a filepath to a subcollection
#
def inventory_by_type(within):
    select_comp_within(within) |
    [ (obj_types|.[]) as $t |
      { "forType": $t,
        "childCount": (select_comp_children(within) |
                       select_obj_type($t) | length),
        "descCount": (select_obj_type($t) | length) } ]
;
def inventory_by_type:
    inventory_by_type("")
;

def inventory_collection(within):
    inventory_by_type(within) as $bt |
    select_comp_within(within) |
    { "forCollection": within,
      "childCount": (select_comp_children(within) | length),
      "descCount": length,
      "byType": $bt,
      "childCollections": [ select_comp_children(within) |
                            select_obj_type("nrdp:Subcollection") |
                            .[] | .filepath ] }
;

def inventory_components:
    [("", (select_obj_type("nrdp:Subcollection") | .[] | .filepath)) as $coll |
     inventory_collection($coll)]
;

# create a hierarchy description of the components within a subcollection
#
# Input: Component array
# Output: a FileHierarcy object
# within: a filepath to the desired subcollection to get a hierarchy for; ""
#           refers to the root collection.
# 
def hierarchy(within):
    select_comp_within(within) | map(select(.filepath)) | . as $desc | 
    select_comp_children(within) |
    map( { filepath, type: .["@type"], } | .filepath as $fp |
         if .type and (.type|contains(["Subcollection"])) then
             .children = ($desc | hierarchy($fp))
         else . end |
         del(.type)
    )  
;

# Return the SRD resource type value if the input POD Dataset appears
# to describe an SRD resource
#
# Input: POD Dataset
# Output: string or empty
#
def isSRD:
    if (.title | test(" - SRD \\d")) then "nrd:SRD" else empty end
;

# Return the resource type value for publid data resource if the input 
# POD Dataset appears to match as such.  All POD records are assumed to
# match
#
# Input: POD Dataset
# Output: string or empty
#
def isPDR:
    "nrdp:PublicDataResource"
;

# Return a list of resource types that an input POD Dataset matches
#
# Input: POD Dataset
# Output: an array of strings
#
def resourceTypes:
    [ isSRD, isPDR ]
;

# Converts an entire POD Dataset node to a NERDm Resource node
#
def podds2resource:
    {
        "@context": nerdm_context,
        "_schema": nerdm_schema,
        "_extensionSchemas": [ nerdm_pub_schema + "/definitions/PublicDataResource" ],
        "@type": resourceTypes,
        "@id": resid,
        "doi": (.distribution + []) | doiFromDist,
        title,
        contactPoint,
        issued,
        modified,

        ediid: .identifier,
        landingPage,
        
        description:  .description | split("\n\n") | map(trimsp|select(length>0)),
        keyword,
        theme,
        topic: [],

        references,
        accessLevel,
        license,
        inventory: [{"forCollection": "", "childCount": 0, "descCount": 0,
                     "byType": [], "childCollections": [] }],
        components: .distribution,
        publisher,
        language,
        bureauCode,
        programCode
    } |
    if .references then .references = (.references | map(cvtref)) else del(.references) end |
    if .components then .components = (.components | map(dist2comp) | insert_subcoll_comps) else del(.components) end |
    if .doi then . else del(.doi) end |
    if .theme then . else del(.theme) end |
    if .issued then . else del(.issued) end |
    if .components then .inventory = (.components | inventory_components) else . end |
    if .components and ((.components|map(select(.filepath))|length) > 0) then .dataHierarchy = (.components|hierarchy("")) else . end |
    if .["@id"] then .["@context"] = [ .["@context"], { "@base": .["@id"] }] else . end 
;

# Converts an entire POD Catalog to an array of NERDm Resource nodes
#
def podcat2resources:
    . | .dataset | map(podds2resource)
;



