#!/bin/bash
set -euo pipefail
mkdir -p /logs/verifier
python /verifier/score.py
