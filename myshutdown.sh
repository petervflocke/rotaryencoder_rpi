#!/bin/sh
echo "starting shutdown..."
sync; sync; sync
sleep 3
/sbin/shutdown now -h
