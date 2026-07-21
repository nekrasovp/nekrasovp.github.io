#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
OUTPUT_DIR=${1:-"${REPOSITORY_ROOT}/.tmp/production"}
cd "${OUTPUT_DIR}"
git init
git remote add origin git@bitbucket.org:Nekrasovp/nekrasovp.bitbucket.io.git
git add -A
git commit -m "Updated static site"
git push --set-upstream origin master -f
