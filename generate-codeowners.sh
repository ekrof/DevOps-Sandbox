#!/bin/bash

ORGANIZATION=${ORGANIZATION}
TE_TEAM=${TE_TEAM}
CUST_TEAM=${CUST_TEAM}
DEFAULT_RULES=${DEFAULT_RULES}
CODEOWNERS_GENERATED=${CODEOWNERS_GENERATED}
CODEOWNERS_TMP=CODEOWNERS_TMP


restrictedResources=(
ClusterRoleBinding
ClusterRole
CustomResourceDefinition
)

files=$(find * \( -name "*yaml" -o -name "*yml" \))

for file in $files;
    do for rs in ${restrictedResources[@]};
        do restrictedFile=( $(yq eval-all 'select(.kind == "'$rs'")|filename' $file) ); for file in $restrictedFile;
            do echo "/$file @$ORGANIZATION/$TE_TEAM" >> $CODEOWNERS_TMP;
            done;
        done;
    done


# Add Default Rules if any
if [[ "$DEFAULT_RULES" != "" ]]; then
  echo "$DEFAULT_RULES" | tr , '\n' > $CODEOWNERS_GENERATED
  cat $CODEOWNERS_TMP >> $CODEOWNERS_GENERATED
else
    echo "no default rules detected"
fi

rm -rf $CODEOWNERS_TMP
