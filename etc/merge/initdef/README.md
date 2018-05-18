This directory contains annotated schemas used to merge NERDm
documents.  Specifically, it contains schemas for the **initdef** merge
conventions, used to initialize generated metadata based the input data
(e.g. from MIDAS) with default values.

Because of limitations of jsonmerge (including its lack of awareness
of ejsonschema conventions), the core NERDm schema is represented by
`nerdm-amalgamated-schema.json` which folds different resource and 
and component types together.

