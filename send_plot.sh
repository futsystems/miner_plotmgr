#!/bin/bash
pv "$1" | nc -q 2 $2 $3
exit
