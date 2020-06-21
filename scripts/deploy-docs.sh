#!/usr/bin/env bash
set -eu
rsync_host=piggie
rsync_dest=/var/www/tormodbot.pastly.xyz

cd docs
sphinx-apidoc -fo . ..
make clean html
rsync -air --delete _build/html/ $rsync_host:$rsync_dest/
