This directory contains annotated schemas used to merge NERDm
documents.  Specifically, it contains schemas for the **pdp0** 
conventions for merging metadata annotations with the base metadata as
done in the PDP implementation of SIP publishing.  In the PDP
implementation, annotations are used to hold metadata values fixed by
the convention, preventing SIP-providing clients from updating them.  

Because of limitations of jsonmerge (including its lack of awareness
of ejsonschema conventions), the core NERDm schema is represented by
`nerdm-amalgamated-schema.json` which folds different resource and 
and component types together.

