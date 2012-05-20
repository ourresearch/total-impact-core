#!/bin/sh
#
# Daily Check
# Providers against the test proxy, and providers against external 
# services 
#

cd ~/total-impact-core
export PYTHONPATH=.:$PYTHONPATH

echo "== Stopping all running services ================"
./service/proxy stop

echo "== Updating to latest git revision =============="
git pull
echo 

echo "== Restart all services ========================="
./service/proxy start

echo "== Running providers check against proxy ========"
export TOTALIMPACT_CONFIG=config/testenv.cfg
./extras/providers_check.py
echo 

echo "== Running providers check against 3rd parties =="
export TOTALIMPACT_CONFIG=config/jenkins.cfg
./extras/providers_check.py
echo 


