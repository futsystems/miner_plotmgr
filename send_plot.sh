#!/bin/bash
echo 'file:'$1' server:'$2' port:'$3
pv "$1" | nc -q 2 $2 $3
exit
