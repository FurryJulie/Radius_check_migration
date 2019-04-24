#!/bin/bash

NOW=$(date -u +%s)
TMP_EXPORT="/tmp/${NOW}_format_radius.txt"

OUT1=$( sed "/Cleartext-Password/!d" ./users )
echo "${OUT1}" > $TMP_EXPORT
OUT2=$( sed  "s/Cleartext-Password :=//g" $TMP_EXPORT )
echo "${OUT2}" > $TMP_EXPORT
OUT3=$( sed  "s/\"//g" $TMP_EXPORT )
echo "${OUT3}" > $TMP_EXPORT
OUT4=$( sed "/ver/!d" $TMP_EXPORT)
echo "${OUT4}" > ./users_formated

rm -f $TMP_EXPORT
