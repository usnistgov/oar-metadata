# JQ library for converting NERDm records to POD
#

# Combine an array of strings representing different paragraphs of text into a
# a single string.  The paragraphs will be delimited by a pair of newline
# characters
#
# Input:   array of strings
# Output:  string
#
def join_para:
    join("\n\n")
;

# Remove contactPoint properties that are not defined in the POD schema
#
# Input:  ContactPoint node
# Output: ContactPoint node
#
def cleanContactPoint:
    { "@type": .["@type"], fn, hasEmail } |
    if (.["@type"]|not) then
        .["@type"] = "vcard:Contact"
    else . end
;

# return true if a given Component has 'dcat:Distribution' included amongst its
# type indicators
#
# Input: NERDm Component node
# Output: boolean
#
def isDistribution:
    if .["@type"] then
        (.["@type"] | [.[] | select(. == "dcat:Distribution")] | length) > 0
    else
        false
    end
;

# convert a single Component into a POD Distribution.
#
# Input:  a NERDm Component node
# Output: a POD Distribution nodes
#
def comp2dist:
    {
      "@type": "dcat:Distribution",
      title,
      description,
      conformsTo,
      describedBy,
      describedByType,
      accessURL,
      downloadURL,
      format,
      mediaType
    } |
    if .title           then . else del(.title)            end |
    if .description     then . else del(.description)      end |
    if .conformsTo      then . else del(.conformsTo)       end |
    if .describedBy     then . else del(.describedBy)      end |
    if .describedByType then . else del(.describedByType)  end |
    if .format          then . else del(.format)           end |
    if .accessURL       then . else del(.accessURL)        end |
    if .downloadURL then
      .
    else
      (del(.downloadURL) |
       if .mediaType then . else del(.mediaType) end)
    end 
;

# convert an array of NERDm Components to an array of Distributions
#
# Input:  array of NERDm Component nodes
# Output: array of POD Distribution nodes
#
def comps2dist:
    [ .[] | select(isDistribution) | comp2dist ]
;

# Convert a DOI from identifier form to URL form
#
def doi2url:
    if startswith("doi:") then
        sub("doi:"; "https://doi.org/")
    else . end
;

# Converts a DOI value to an access distribution using the MIDAS convention
#
# Input: a DOI value (in doi: form)
# Output: a Distribution node
#
def doi2dist:
    doi2url | {
      "@type": "dcat:Distribution",
      "accessURL": .,
      "format": "text/html",
      "title": "DOI Access"
    }
;

# Given a list of POD distributions, find those matching a DOI access
# distribution that follows the MIDAS convention
#
# Input:  array of Distribution nodes
# Output: the matching Distribution node or null if not found
# 
def findDOIdist:
    [ .[] | select(.accessURL) |
      select(.accessURL|startswith("https://doi.org/")) ] |
    if length > 0 then .[0] else null end
;

# Converts a NERDm Resource to a POD Dataset
#
# Input: a NERDm Resource node
# Output: a POD Dataset node
#
def resource2midaspodds:
    {
        "@type": "dcat:Dataset",
        identifier: .ediid,
        "@id": .["@id"],
        doi, 
        title,
        modified,
        issued,
        contactPoint: .contactPoint | cleanContactPoint,
        description,
        landingPage,
        keyword,
        theme,
        isPartOf,
        references,
        publisher,
        license,
        accessLevel,
        rights,
        conformsTo,
        language,
        dataQuality,
        accrualPeriodicity,
        bureauCode,
        programCode,
        systemOfRecords,
        primaryITInvestmentUII,
        distribution: .components
    } |
    if (.identifier|not) then .identifier = .["@id"] else . end | del(.["@id"]) |
    if (.description|length) > 0 then .description = (.description|join_para)
                                 else .description = ""              end |
    if .isPartOf and .isPart["@id"] then .isPartOf = .isPartOf["@id"]
                                    else del(.isPartOf)              end |
    if .references then .references = [ .references[] | select(.location) |
                                        .location ]
                   else del(.references)                             end |
    if (.bureauCode|not)  then .bureauCode  = ["006:55"]  else .     end |
    if (.programCode|not) then .programCode = ["006:045"] else .     end |
    if (.language|not)    then .language    = ["en"]      else .     end |
    if (.accessLevel|not) then .accessLevel = "public"    else .     end |
    if .systemOfRecords  then . else del(.systemOfRecords)           end |
    if .accrualPeriodicity  then . else del(.accrualPeriodicity)     end |
    if .dataQuality  then . else del(.dataQuality)                   end |
    if .primaryITInvestmentUII  then . else del(.primaryITInvestmentUII) end |
    if .rights       then . else del(.rights)                        end |
    if .license      then . else del(.license)                       end |
    if .theme then .theme = [.theme|.[]|gsub(":"; "->")] else del(.theme) end |
    if .issued       then . else del(.issued)                        end |
    if .conformsTo   then . else del(.conformsTo)                    end |
    if .distribution then
        .distribution = (.distribution|comps2dist) 
    else
        .distribution = []
    end |
    if .doi and (.distribution | findDOIdist | not) then
        .distribution = [.doi | doi2dist] + .distribution |
        if .title then
            .title as $title | 
            .distribution[0] = (.distribution[0] |
                                .title = .title + " for " + $title |
                                .description = .title)
        else . end
    else . end |
    if .distribution and (.distribution|length) > 0 then
        . else del(.distribution)
    end |
    del(.doi) |
    .
;

