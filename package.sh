#!/bin/bash

BuildDir=`mktemp -d /tmp/package-XXXXXX`

function usage {
    echo ""
    echo "Usage: $1 <AppFolder> <DSYMFolder> <ResultName>"
    echo ""
    echo "<AppFolder>  is absolute path to *.app"
    echo "<DSYMFolder> is absolute path to *.dsym"
    echo "<ResultName> is the name for resulting package file in the current directory"
    echo ""
    echo "Following is resulting package structure:"
    echo ""
    echo "<ResultName>.zip/DSYM/<ResultName>.dSYM"
    echo "<ResultName>.zip/<ResultName>.ipa"
    echo ""
}

function remove_build_dir {
    if [ -d "$BuildDir" ]
    then
        cd /
        rm -rf "$BuildDir"
    fi
}

function exit_if_error {
    if [ $? -ne 0 ]
    then
        echo "$1"
        remove_build_dir
        exit 1
    fi
}

if [ $# -ne 3 ]
then
    usage $0
    exit 1
fi

AppFolder="$1"
DSYMFolder="$2"
ResultName="$3"

if [ -f "$ResultName".zip ]
then
    rm "$ResultName".zip
    exit_if_error "Failed removing previous package"
fi

cd "$BuildDir"
exit_if_error "Failed to change dir"

mkdir Payload
exit_if_error "Failed to create 'Payload' directory'"

mkdir DSYM
exit_if_error "Failded to create 'DSYM' directory"

cp -rp "$AppFolder" Payload/
exit_if_error "Failed to copy application bundle into 'Payload' folder"

zip -ry "$ResultName".ipa Payload
exit_if_error "Failed to zip 'Payload'"

cp -rp "$DSYMFolder" DSYM/
exit_if_error "Failed to copy 'dsym' into destination folder'"

zip -ry "$ResultName".zip "$ResultName".ipa DSYM
exit_if_error "Failed to create final 'zip'"

cd -
exit_if_error "Failed to change directory to original"

cp "$BuildDir"/"$ResultName".zip .
exit_if_error "Failed to copy resulting package"

remove_build_dir
