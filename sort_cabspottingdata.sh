#!/bin/sh
#
# Sort the files in cabspottingdata according
# to their unix timestamps
#
for i in cabspottingdata/new_*
do
    echo $i
    sort -n --key=4 $i > /tmp/cabspottingdata.txt
    mv /tmp/cabspottingdata.txt $i
done
