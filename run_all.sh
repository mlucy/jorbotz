# set -eu

for i in formatted/*; do
    echo $i
    python3 reformat_run.py $i
done
