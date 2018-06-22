#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR
LAST=$(git rev-parse HEAD)
git pull
CURR=$(git rev-parse HEAD)
if [ "$LAST" != "$CURR" ]
then
    tmux kill-session -t unsafepay
    tmux new -ds unsafepay "PATH=$PATH:/usr/local/bin ~/.virtualenvs/unsafepay/bin/python $DIR/bot.py"
fi
