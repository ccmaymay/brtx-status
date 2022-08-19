#!/bin/bash

set -e

cd dist
for f in index.html assets/*
do
    aws s3 cp $f s3://brtx-status/$f
done