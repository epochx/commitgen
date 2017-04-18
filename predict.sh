#!/bin/bash

FILE_NAME=$1
LANGUAGE=$2
GPUIDX=${3-1}
BEAMSIZE=10

# Run prediction
th ./model/predict.lua -dataset ${FILE_NAME} -encoder ${FILE_NAME}.${LANGUAGE}.encoder -decoder ${FILE_NAME}.${LANGUAGE}.decoder -beamsize $BEAMSIZE -gpuidx $GPUIDX -language ${LANGUAGE}
