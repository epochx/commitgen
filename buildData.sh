#!/bin/bash

FILE_NAME=$1
LANGUAGE=$2

# Create working directory
if [ ! -d "$WORK_DIR" ]; then
	mkdir -p $WORK_DIR/preprocessing
fi

CODE_MAX_LENGTH=100
NL_MAX_LENGTH=100
CODE_UNK_THRESHOLD=3
NL_UNK_THRESHOLD=2
BATCH_SIZE=100

python buildData.py $FILE_NAME -l $LANGUAGE -cml $CODE_MAX_LENGTH -nml $NL_MAX_LENGTH -cut $CODE_UNK_THRESHOLD -nut $NL_UNK_THRESHOLD -t -r 0.95
th buildData.lua -dataset $FILE_NAME -language $LANGUAGE -max_code_length $CODE_MAX_LENGTH -max_nl_length $NL_MAX_LENGTH -batch_size $BATCH_SIZE
