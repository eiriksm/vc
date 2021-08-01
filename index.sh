#!/bin/bash

function dowrite () {
    echo "window.imagePaths = [";

    for i in `ls -1t results/*.png`; do
        echo "'$i',";
    done
    
    echo "];window.handler.drawImages();"
}

while true; do
    rsync -av vc:/opt/vc/results/ results/
    dowrite > images.js
    sleep 10
done