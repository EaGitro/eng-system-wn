#!/bin/sh

# install pip library
pip install -r requirements.txt;

# install en_core_web_md
python -m spacy download en_core_web_md;

# install wnjp

wd=$(pwd);

wget https://github.com/bond-lab/wnja/releases/download/v1.1/wnjpn.db.gz -P $wd/data/ && 
gzip -dc $wd/data/wnjpn.db.gz > $wd/data/wnjpn.db

