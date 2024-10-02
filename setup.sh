#!/bin/sh

# install pip library
pip install -r requirements.txt;

# install en_core_web_md
python -m spacy download en_core_web_md;

# install wnjp

dbdir="$(pwd)/db";

wget https://github.com/bond-lab/wnja/releases/download/v1.1/wnjpn.db.gz -P "$dbdir/" && 
gzip -dc "$dbdir/wnjpn.db.gz" > "$dbdir/wnjpn.db"

