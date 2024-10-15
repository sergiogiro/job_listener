import json
import os
from datetime import datetime

from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.providers.amazon.aws.sensors.sqs import SqsSensor

from airflow import DAG

with DAG(
    dag_id="listen-for-job-requests",
    schedule="@continuous",
    start_date=datetime(2024, 10, 14),
    max_active_runs=1,
    user_defined_filters={"from_json_string": lambda s: json.loads(s)},
) as dag:
    poll_for_job_messages = SqsSensor(
        task_id="poll-sqs-job-message-sensor",
        sqs_queue=os.environ["SQS_JOBS_QUEUE_URL"],
        region_name=os.environ["SQS_JOBS_QUEUE_REGION"],
        # According to the documentation, this is the maximum value allowed for
        # the waiting time before returning with an empty response.
        wait_time_seconds=20,
        # Re-poke right after no messages have been found.
        poke_interval=0,
        # A one-week time out will start a new "listening" DAG if no messages
        # show up for a week (or after 1000000 million retries).
        timeout=60 * 60 * 24 * 7,
        retries=1000000,
        deferrable=True,
        max_messages=1,
    )

    MESSAGE_TEMPLATE = (
        "task_instance.xcom_pull("
        "    task_ids='poll-sqs-job-message-sensor', key='messages'"
        ")[0]"
    )
    MESSAGE_BODY_TEMPLATE = f"({MESSAGE_TEMPLATE}['Body'] | from_json_string)"
    run_job_dag = TriggerDagRunOperator(
        task_id="run-job-dag-operator",
        trigger_dag_id="run-job",
        trigger_run_id=f"{{{{ {MESSAGE_TEMPLATE}['MessageId'] }}}}",
        wait_for_completion=False,
        deferrable=True,
        conf={
            k: f"{{{{ {MESSAGE_BODY_TEMPLATE}['{k}'] }}}}"
            for k in ("repo_uri", "branch", "entrypoint", "entrypoint_params")
        },
    )

    poll_for_job_messages >> run_job_dag
