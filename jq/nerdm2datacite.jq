# JQ library for converting NERDm records to Datacite Metadata
#

# return true if the string represents a DOI
#
# Input:  string
# Output: boolean
#
def is_DOI:
    startswith("doi:") or test("^https?://(\\w+.)?doi.org/")
;

# strip prefixes from a DOI identifier
#
# Input: DOI string
# Output: string
#
def stripDOI:
    sub("^doi:"; "") | sub("^https?://(\\w+.)?doi.org/"; "")
;

# convert a DOI PID to its URL form
#
# Input:  DOI string
# Output: URL string
#
def todoiurl:
    if (is_DOI) then
        "https://doi.org/" + stripDOI
    else
        .
    end
;

# strip the time portion of a date string if it is set to exactly midnight
#
# Input: date string
# Output: string
#
def stripMidnight:
    sub("[ T]00:00:00(.0+)*$"; "")
;

# return true if a component is a datafile
#
# Input:  component
# Output: boolean
#
def is_datafile:
    .["@type"] | map(select(contains(":DataFile"))) | length > 0
;

# Determine whether the contactPoint refers to a person or an
# organizational group
#
# Input: ContactPoint object
# Output: string, either "Personal" or "Organizational"
#
def contact_type:
    if (.hasEmail | test("^(mailto:)?\\w+\\.\\w+@nist.gov")) then
        "Personal"
    else
        "Organizational"
    end
;

# Converts the contact info into a creators list
#
# Input: contactPoint object
# Ouput: creators list
#
def contactPoint2creators:
    [
      {
        name: .fn,
        nameType: .|contact_type
      }
    ]
;

# Converts the contact info into a creators list
#
# Input:  contactPoint object
# Output: contributor object
#
def contactPoint2contributor:
    {
      name: .fn,
      nameType: .|contact_type,
      contributorType: "ContactPerson"
    }
;

# Convert an ORCID to a datacite nameIdentifier
#
# Input:  orcid string
# Output: nameIdentifier object
#
def orcid2nameid:
    {
        nameIdentifier: ("https://orcid.org/" + .),
        nameIdentifierScheme: "ORCID",
        schemeURI: "https://orcid.org"
    }
;

# Convert a NERDm affiliation object to a datacite affliation string
#
# Input:  NERDm affiliation object
# Output: datacite affiliation string
#
def affil2simpleaffil:
    if .subunits then
        (.title + ", " + (.subunits | join(", ")))
    else
        .title
    end
;

# Convert a NERDm affiliation object to a datacite affliation object
#
# Input:  NERDm affiliation object
# Output: datacite affiliation object
#
def affil2affil:
    {
        affiliation: affil2simpleaffil,
        affiliationIdentifier: .["@id"],
        affiliationIdentifierScheme:  (
            if (.["@id"] and (.["@id"] | test("^grid:"))) then "GRID"
            else null end
        ),
    } |
    if (.affiliationIdentifier|startswith("ror:") then
        (.affiliationIdentifier = (.affiliationIdentifier|sub("ror:";"https://ror.org/")|
         .affiliationIdentifierScheme = "ROR")
    elif (.affiliationIdentifer == "grid.94225.38" or
        (.affiliation | contains("National Institute of Standards and Technology"))) then
        (.affiliationIdentifier = "https://ror.org/05xpvk416" |
         .affiliationIdentifierScheme = "ROR")
    else . end | 
    if .affiliationIdentifierScheme then .
    else (del(.affiliationIdentifier) | del(.affiliationIdentifierScheme)) end
;

# Convert a NERDm affiliation object to a datacite affliation object
#
# Input:  list of NERDm affiliations
# Output: list of NERDm affiliation object
#
def affils2affils:
    map(affil2affil)
;

# Converts an author list to a creator
#
# Input:  author object
# Output: creator object
# 
def author2creator:
    {
        name: .fn,
        nameType: (if .givenName then "Personal" else "Organizational" end),
        givenName: (
            if .givenName and .middleName then
                .givenName+" "+.middleName
            else
                .givenName
            end
        ),
        familyName: .familyName,
        nameIdentifiers: (if .orcid then (.orcid|[orcid2nameid]) else null end),
        affiliation: .affiliation | affils2affils
    } |
    if .givenName      then . else del(.givenName) end |
    if .familyName     then . else del(.familyName) end |
    if .nameIdentifers then . else del(.nameIdentifiers) end |
    if .affiliation    then . else del(.affiliation) end |
    if .familyName and .givenName then
        (.name = .familyName + ", " + .givenName)
    else . end
;

# Converts the authors list to a creators list
#
# Input:  authors list
# Output: creators list
# 
def authors2creators:
    map(author2creator)
;

# Create a creator listing from a NERDm resource's authors, if they exist, or
# its contactPoint
#
# Input:  resource object
# Output: creators list
# 
def make_creators:
    if .authors then
       (.authors | authors2creators)
    else
       (.contactPoint | contactPoint2creators)
    end
;

# Create a datacite titles array from information in the NERDm resource
#
# Input:  resource object
# Output: titles list
#
def make_titles:
    [
      (
        (.title | { title: . }),
        (.subtitle | {
          title: .,
          titleType: "Subtitle"
        }),
        (.aka | {
          title: .,
          titleType: "Other"
        }) | select(.title)
      )
    ]
;

# Extract the year field from a date string
#
# Input:  date string
# Output: year string
#
def get_year:
    sub(":.*$"; "")
;

# Create a datacite titles array from information in the NERDm resource
#
# Input:  resource object
# Output: year string
#
def make_pubyear:
    if .issued then
        (.issued | get_year)
    elif .modified then
        (.modified | get_year)
    else null end
;

# Create datacite dates array from information in the NERDm resource
#
# Input:  resource object
# Output: dates list
#
def make_dates:
    [
      (
        (.issued | {
          date: .,
          dateType: "Issued"
        }),
        (.modified | {
          date: .,
          dateType: "Updated"
        })
      ) | select(.date) | .date = (.date|stripMidnight)
    ]
;

# print a tallying of the number of files (e.g. "40 files")
#
# Input:  components list
# Output: string
#
def count_files:
    map(select(is_datafile)) | length |
    if (. > 0) then 
        tostring + " files"
    else
        empty
    end
;

# format a number of bytes into a string with units
#
# Input:  number
# Output: string
#
def format_size:
    [ "bytes", "kB", "MB", "GB", "TB" ] as $units |
    (if (. > 0) then (log10 | floor) else 0 end) as $ordr | 
    ($ordr / 3 | floor | if (. > 4) then 4 else . end) as $sc |
    (
      . / ($sc * 3 | pow10) |
      if (. < 10) then
         (. * 100 | round / 100)
      else
         (. * 10 | round / 10)
      end |
      tostring
    ) + " " + $units[$sc]
;

# print a tallying of the total size of all data files (e.g. "105.3 MB")
#
# Input:  components list
# Output: string
#
def total_size:
    map(select(is_datafile)) | reduce .[].size as $sz (0; . + $sz) |
    if (. > 0) then
        format_size
    else
        empty
    end
;

# Extract a unique list of media formats extracted from the give list
# of components
#
# Input:  components list
# Output: string list
#
def make_formats:
    map(select(is_datafile) | .mediaType | select(.)) | unique
;

# convert a isPartOf object into a related identifier object
#
def make_ispartof_rel:
    if (.["@id"] and (.["@id"] | contains("doi"))) then
      {
        relatedIdentifier: .["@id"] | todoiurl,
        relatedIdentifierType: "DOI",
        relationType: "isPartOf"
      }
    elif (.location) then
      {
        relatedIdentifier: (.location | todoiurl),
        relationType: "isPartOf"
      } |
      if (.relatedIdentifier | test("^https?://(dx.)?doi.org/")) then
          (.relatedIdentifierType = "DOI")
      else
          (.relatedIdentifierType = "URL")
      end
    else
      empty
    end
;

# convert a reference object into a related identifier object
#
def make_ref_rel:
    (
      if (.pid) then
          (.pid | todoiurl)
      elif (.proxyFor and (.proxyFor|is_DOI)) then
          (.proxyFor | todoiurl)
      else
          .location
      end
    ) as $refid |
    if ($refid) then
      (
        {
          relatedIdentifier: $refid,
          relationType: .refType
        } |
        if .relationType then . else .relationType = "References" end |
        if (.relatedIdentifier | is_DOI) then
            (.relatedIdentifierType = "DOI")
        else
            (.relatedIdentifierType = "URL")
        end
      )
    else
      empty
    end
;

# Converts a NERDm Resource to a DataCite attributes object
#
# Input:  resource object
# Output: datacite attributes object
#
def resource2datacite:
    {
      doi,
      titles: make_titles,
      creators: make_creators,
      contributors: [ .contactPoint | contactPoint2contributor ],
      publisher: .publisher.name,
      publicationYear: make_pubyear,
      types: {
        "resourceType": .["@type"][0],
        "resourceTypeGeneral": "Dataset",
        "citeproc": "dataset",
        "schemaOrg": "Dataset"
      },
      url: .landingPage,
      schemaVersion: "http://datacite.org/schema/kernel-4",
      version,
      dates: make_dates,
      subjects: .themes,
      sizes: [ .components | (count_files, total_size) ],
      formats: .components | make_formats,
      alternateIdentifiers: [
        {
          alternateIdentifier: .ediid,
          alternateIdentifierType: "data.gov POD identifier"
        }
      ],
      relatedIdentifiers: [
        (
          (.isPartOf | make_ispartof_rel),
          (.references | if (.) then (.[] | make_ref_rel) else empty end)
        )
      ],
      language: "en-US"
    } | 
    if .doi then .doi = (.doi | stripDOI) else del(.doi) end |
    if .version then . else .version = "1.0.0" end |
    if .subjects then . else .subjects = [] end |
    if ((.sizes | length) > 0) then . else del(.sizes) end |
    if ((.relatedIdentifiers | length) > 0) then .
    else del(.relatedIdentifiers) end 
;


