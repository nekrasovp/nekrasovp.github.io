#!/usr/bin/env bash
OUTPUT_DIR=../output/
cd ${OUTPUT_DIR}
git init
git remote add origin git@bitbucket.org:Nekrasovp/nekrasovp.bitbucket.io.git
git add -A
git commit -m "New blog post"
git push --set-upstream origin master -f