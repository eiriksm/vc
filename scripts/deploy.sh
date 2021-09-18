#!/bin/bash

ssh vc "
cd /opt/vc
git pull origin \$\(git rev-parse --abbrev-ref HEAD\)
sudo service supervisor restart
flask db migrate
npx webpack
"
