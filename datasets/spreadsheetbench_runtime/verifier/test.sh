#!/bin/bash
set -euo pipefail
mkdir -p /logs/verifier
exec python /verifier/score.py
