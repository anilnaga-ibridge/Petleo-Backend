#!/bin/bash

echo "--- Testing Target: individual ---"
curl -s "http://127.0.0.1:8002/api/provider/documents/definitions/?target=individual" | python3 -m json.tool

echo "\n\n--- Testing Target: organization ---"
curl -s "http://127.0.0.1:8002/api/provider/documents/definitions/?target=organization" | python3 -m json.tool
