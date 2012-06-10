#!/bin/bash

new_version=$1

if [[ $new_version =~ ^[0-9]+\.[0-9]+\.[0-9] ]] ; then
    echo "Bumping version to $new_version"
    sed -i 's/^\( \+\)version="[0-9]\+\.[0-9]\+\.[0-9]\+[^"]*"$/\1version="'$new_version'"/' addon.xml
    sed -i 's/^version = "[0-9]\+\.[0-9]\+\.[0-9]\+[^"]*"$/version = "'$new_version'"/' default.py
else
    echo "Invalid new version number"
fi

