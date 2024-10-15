import json
import os
import uuid

import boto3
from airflow.decorators import task
from airflow.models.param import Param

from airflow import DAG

with DAG(
    dag_id="send-test-sqs-message",
    schedule=None,
    params={
        "repo_uri": Param(
            type="string",
            title="Repo URI",
            description="URI of the repo. Use github.com/org/rep for "
            "https://github.com/org/rep (works over https only)",
            default="github.com/sergiogiro/job_listener",
        ),
        "branch": Param(
            type="string",
            title="Branch",
            description="The branch to run",
            default="master",
        ),
        "entrypoint": Param(
            type="string",
            title="Entrypoint",
            description="The path of the execute to run inside the repo. "
            "Use ./entrypoint.script if entrypoint.script is at the "
            "root of your repo",
            default="python -u example_job/mat_mul.py",
        ),
        "entrypoint_params": Param(
            type=["null", "string"],
            title="String to pass to the entrypoint in the variable "
            "ENTRYPOINT_PARAMS",
            default="[15000, 30000, 16000]",
        ),
    },
) as dag:

    @task
    def send_test_message(params):
        # Can't use the SqsPublish operator since it doesn't support
        # the (needed) MessageDeduplicationId.
        queue = boto3.resource(
            "sqs",
            region_name=os.environ["SQS_JOBS_QUEUE_REGION"],
        ).Queue(
            os.environ["SQS_JOBS_QUEUE_URL"],
        )
        deduplication_id = str(uuid.uuid4())
        print("Sending message with deduplication id:", deduplication_id)
        queue.send_message(
            MessageBody=json.dumps(params),
            MessageDeduplicationId=deduplication_id,
            MessageGroupId="0",
        )

    send_test_message()
