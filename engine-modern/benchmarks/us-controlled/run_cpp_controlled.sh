#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 4 ]]; then
  echo "usage: run_cpp_controlled.sh <dwnominate-modern> <us-cpp-input> <common-seed.csv> <output-dir>" >&2
  exit 2
fi

binary=$1
input_dir=$2
seed=$3
output_dir=$4

if [[ ! -x "$binary" ]]; then
  echo "C++ binary is not executable: $binary" >&2
  exit 2
fi
if [[ ! -f "$seed" ]]; then
  echo "common seed does not exist: $seed" >&2
  exit 2
fi
if [[ -e "$output_dir" ]]; then
  echo "output directory already exists: $output_dir" >&2
  exit 2
fi

"$binary" \
  --input-dir="$input_dir" \
  --output-dir="$output_dir" \
  --wnominate="$seed" \
  --periods=5 \
  --model=1 \
  --iterations=5 \
  --dimensions=2 \
  --beta=5.9539 \
  --w2=0.3463 \
  --optimizer-precision=standard
