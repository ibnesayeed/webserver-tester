#!/usr/bin/env bash

# export TZ="America/New_York"
export TZ="UTC"
dt=`date +"%Y%m%d%H%M%S%Z"`

suite=${1:-example}
tag=$suite
if [[ "$suite" == "echo" ]] || [[ "$suite" == "example" ]]
then
    tag="master"
fi

outdir=${2:-reports}

while IFS=, read -r csid name ghid repo
do
    if [[ "$csid" == "csid" ]]
    then
        continue
    fi
    suitedir="$outdir/$csid/$suite"
    mkdir -p $suitedir
    reort="$suitedir/$csid-$suite-$dt.txt"
    echo "Creating report: $reort"

    echo "================================================================================" > $reort
    echo "Assignment: $suite" >> $reort
    echo "Student: $name <$csid@cs.odu.edu>" >> $reort
    echo "Time: $dt" >> $reort
    echo "Repository: https://github.com/$ghid/$repo/tree/$tag" >> $reort
    echo "Server: cs531-$csid" >> $reort
    echo "================================================================================" >> $reort

    echo "" >> $reort
    echo "Deploying server: cs531-$csid" | tee -a $reort
    echo "" >> $reort
    curl -is "http://cs531.cs.odu.edu/servers/deploy/$csid/$tag" >> $reort

    sleep 5

    echo "" >> $reort
    echo "Testing server: cs531-$csid against $suite test suite" | tee -a $reort
    echo "" >> $reort
    ./main.py "cs531-$csid" $suite >> $reort

    echo "" >> $reort
    echo "Destroying server: cs531-$csid" | tee -a $reort
    curl -is "http://cs531.cs.odu.edu/servers/destroy/$csid" >> $reort
    echo "" >> $reort
done

echo "All done!"
