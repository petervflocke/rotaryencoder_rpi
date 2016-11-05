#!/bin/sh
for file in /var/log/*.log
 do
   > $file
 done
 rm -f /var/log/*.gz
  > /var/log/syslog
 echo "" > /var/log/messages
 echo "" > /var/log/debug

