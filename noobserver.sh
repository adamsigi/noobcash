#!/bin/bash
export FLASK_APP=endpoints
export NUMBER_OF_NODES=3
export DIFFICULTY=4
export BOOTSTRAP_IP=127.0.0.1
export BOOTSTRAP_PORT=5000
export NODE_PORT=$1
export CAPACITY=3
export TOTAL_COINS=1000

if [ $1 ]
then 
    waitress-serve --port=$1 endpoints:app
else
    waitress-serve --port=$BOOTSTRAP_PORT endpoints:app
fi