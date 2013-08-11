#!/bin/bash
while read e; do
  export $e
done < .env-local

nosy -c test/nosy.cfg