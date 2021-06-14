#!/bin/bash
echo 'file:'$1' server:'$2' port:4040'
sudo /usr/bin/pv "$1" | sudo /usr/bin/nc -q 2 $2 4040
exit
