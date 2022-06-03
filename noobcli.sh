#!/bin/bash
export NODE_IP=$1
export NODE_PORT=$2

if [ $# -eq 2 ]
then 
    python3 cli_client.py
else
    echo "Usage: noobcli.sh <IP> <PORT>"
fi