#!/bin/bash
sudo /usr/bin/pv "$1" | sudo /usr/bin/nc -q 5 $2 4040
exit
