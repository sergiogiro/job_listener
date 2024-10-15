#!/usr/bin/env bash

########################################################
# Usual boilerplate to get the directory of this script.
########################################################

SOURCE=${BASH_SOURCE[0]}
# resolve $SOURCE until the file is no longer a symlink
while [ -L "$SOURCE" ]; do
  DIR=$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )
  SOURCE=$(readlink "$SOURCE")
  # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
  [[ $SOURCE != /* ]] && SOURCE=$DIR/$SOURCE
done
DIR=$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )

if [[ -z "$1" ]]; then
    SQS_JOBS_QUEUE_URL=$"$(terraform -chdir="$DIR/../terraform" output -raw queue_url)"
else
    SQS_JOBS_QUEUE_URL="$1"
fi

shift

if [[ -z "$1" ]]; then
    SQS_JOBS_QUEUE_REGION=$"$(terraform -chdir="$DIR/../terraform" output -raw queue_region)"
else
    SQS_JOBS_QUEUE_REGION="$1"
fi



docker build worker_image -t job_listener_worker

SQS_JOBS_QUEUE_URL="$SQS_JOBS_QUEUE_URL" \
    SQS_JOBS_QUEUE_REGION="$SQS_JOBS_QUEUE_REGION" \
    AIRFLOW_PROJ_DIR="${DIR}/proj_dir" \
    docker compose up -d --build
