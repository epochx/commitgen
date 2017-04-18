#!/bin/bash

FILE_NAME=$1
LANGUAGE=$2
GPUIDX=${3-1}
BEAMSIZE=10

# Run Training
th ./model/main.lua -dataset $FILE_NAME -gpuidx $GPUIDX -language $LANGUAGE
