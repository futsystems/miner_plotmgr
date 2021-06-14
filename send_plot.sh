#!/bin/bash
sudo /usr/bin/pv "$1" | sudo /usr/bin/nc -q 2 $2 $3
exit
