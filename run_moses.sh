#!/bin/bash

if [ ! -d "$WORK_DIR" ]; then
	mkdir -p $WORK_DIR/moses/{data,lm}
fi

DATASET=$1
LANGUAGE=$2

# copy generated files for moses
cp $WORK_DIR/preprocessing/$DATASET.$LANGUAGE.*.code $WORK_DIR/moses/data
cp $WORK_DIR/preprocessing/$DATASET.$LANGUAGE.*.nl $WORK_DIR/moses/data

BASEDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd $WORK_DIR/moses

# if needed, clean training files
#~/mosesdecoder/scripts/training/clean-corpus-n.perl ./$DATASET.$LANGUAGE.train code nl ./$DATASET.$LANGUAGE.train.clean 1 100
# mv ./$DATASET.$LANGUAGE.train.clean.nl ./$DATASET.$LANGUAGE.train.nl
# mv ./$DATASET.$LANGUAGE.train.clean.code ./$DATASET.$LANGUAGE.train.code

# remove previous files
rm *.out
rm ./lm/*
rm -r ./trained
rm -r ./mert-work

# train LM on the "target language" i.e. natural language training data
~/mosesdecoder/bin/lmplz -o 3 < ./data/$DATASET.$LANGUAGE.train.nl > ./lm/$DATASET.$LANGUAGE.train.arpa.nl

# generate binary trained lm
~/mosesdecoder/bin/build_binary ./lm/$DATASET.$LANGUAGE.train.arpa.nl ./lm/$DATASET.$LANGUAGE.train.blm.nl

# training
nice ~/mosesdecoder/scripts/training/train-model.perl -root-dir trained -corpus ./data/$DATASET.$LANGUAGE.train -f code -e nl -alignment grow-diag-final-and -reordering msd-bidirectional-fe -lm 0:3:$WORK_DIR/moses/lm/$DATASET.$LANGUAGE.train.blm.nl:8 -external-bin-dir ./bin/training-tools -mgiza -mgiza-cpus 8 > training.out

# validation
nice ~/mosesdecoder/scripts/training/mert-moses.pl ./data/$DATASET.$LANGUAGE.valid.code ./data/$DATASET.$LANGUAGE.valid.nl ~/mosesdecoder/bin/moses ./trained/model/moses.ini --mertdir ~/mosesdecoder/bin/ > mert.out --decoder-flags="-threads 8"

# generate translation
nice ~/mosesdecoder/bin/moses -f ./trained/model/moses.ini < ./data/$DATASET.$LANGUAGE.test.code > ./data/$DATASET.$LANGUAGE.translated.nl 2> test.out

# add line numbers for bleu
nl -n ln ./data/$DATASET.$LANGUAGE.test.nl > ./data/$DATASET.$LANGUAGE.test.nl.num
nl -n ln ./data/$DATASET.$LANGUAGE.translated.nl > ./data/$DATASET.$LANGUAGE.translated.nl.num

# evaluate
python $BASEDIR/model/bleu.py $WORK_DIR/moses/data/$DATASET.$LANGUAGE.test.nl.num < $WORK_DIR/moses/data/$DATASET.$LANGUAGE.translated.nl.num




