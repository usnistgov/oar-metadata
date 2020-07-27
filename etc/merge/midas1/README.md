This directory contains annotated schemas used to merge NERDm
documents.  Specifically, it contains schemas for the **midas1** merge
conventions, used to merge PDR annotations (representing author
customizations) into base metadata generated from MIDAS (via the POD
record) according to the revised (labeled "1") policy governing metadata
updates.  This policy allows core metadata--that is, metadata covered
by the POD record--to be updated by annotations as long as the
affected POD metadata are sent back to MIDAS to be updated.  
This merge convention enables this policy.

Because of limitations of jsonmerge (including its lack of awareness
of ejsonschema conventions), the core NERDm schema is represented by
`nerdm-amalgamated-schema.json` which folds different resource and 
and component types together.

