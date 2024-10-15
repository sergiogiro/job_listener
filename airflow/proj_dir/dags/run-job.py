import os
import shlex
import uuid

from airflow.decorators import task
from airflow.models.param import Param
from airflow.operators.bash import BashOperator
from pathvalidate import validate_filepath

from airflow import DAG

REPO_PATH_PREFIX = "/home/airflow/repos"
TEMP_REPOS_DIR = "/home/airflow/temp_repos"


# Disable quirk that makes templates kick in only when ".sh"
# is present in a string.
# https://github.com/apache/airflow/issues/1017
BashOperator.template_ext = ()


with DAG(
    dag_id="run-job",
    schedule=None,
    params={
        "repo_uri": Param(
            type="string",
            title="Repo URI",
            description="URI of the repo. Use github.com/org/rep for "
            "https://github.com/org/rep (works over https only)",
        ),
        "branch": Param(
            type="string",
            title="Branch",
            description="The branch to run",
        ),
        "entrypoint": Param(
            type="string",
            title="Entrypoint",
            description="The path of the execute to run inside the repo. "
            "Use ./entrypoint.script if entrypoint.script is at the "
            "root of your repo",
        ),
        "entrypoint_params": Param(
            type=["null", "string"],
            title="String to pass to the entrypoint in the variable "
            "ENTRYPOINT_PARAMS",
            default="",
        ),
    },
) as dag:

    @task
    def generate_temp_repo_prefix() -> str:
        return shlex.quote(str(uuid.uuid4()))

    @task
    def get_repo_path(params: dict[str, any]) -> str:
        repo_uri = params["repo_uri"]
        # Keep the last two parts separated by "/" as to support
        # org/repo format.
        parts = [part for part in repo_uri.split("/") if len(part) > 0][-2:]

        invalid_uri_message = f"Invalid repo_uri: {repo_uri}"
        if len(parts) == 0:
            raise ValueError(invalid_uri_message)
        for p in parts:
            if p in [".", ".."]:
                raise ValueError(invalid_uri_message)
        path = os.path.join(*parts)
        validate_filepath(path)
        return shlex.quote(os.path.join(REPO_PATH_PREFIX, path))

    @task
    def sanitised_branch(params: dict[str, any]) -> str:
        return shlex.quote(params["branch"].strip())

    @task
    def sanitised_repo_uri(params: dict[str, any]) -> str:
        return shlex.quote("https://" + params["repo_uri"].strip())

    @task
    def sanitised_entrypoint(params: dict[str, any]) -> str:
        return shlex.quote(params["entrypoint"].strip())

    temp_repo_prefix = generate_temp_repo_prefix()
    repo_path = get_repo_path()
    branch = sanitised_branch()
    repo_uri = sanitised_repo_uri()
    entrypoint = sanitised_entrypoint()

    @task.bash(
        env={
            "GIT_USERNAME": os.environ["GIT_USERNAME"],
            "GIT_PASSWORD": os.environ["GIT_PASSWORD"],
        },
        append_env=True,
        # Prevent several tasks creating the same repo at the
        # same time. More strictly than needed, since this
        # restricts parallelism even if it's a different repo.
        # Airflow doesn't allow for more granularity.
        # Hopefully a new repo would be a rare event and this
        # would be ok.
        max_active_tis_per_dag=1,
    )
    def create_repo_if_needed(repo_uri: str, repo_path: str) -> None:
        return (
            # Magic return value to mark the task as skipped.
            f"[ -d {repo_path} ] && exit 99;"
            f"git clone {repo_uri} {repo_path} "
            # Remove dir in case something fails.
            f"    || rm -r {repo_path}"
        )

    # Fetch the branch and create local branch with the temporary prefix.
    @task.bash(
        env={
            "GIT_USERNAME": os.environ["GIT_USERNAME"],
            "GIT_PASSWORD": os.environ["GIT_PASSWORD"],
        },
        append_env=True,
        cwd=repo_path,
        trigger_rule="none_failed",
    )
    def git_fetch_at_repo(repo_path: str, branch: str) -> None:
        return (
            f"git config --global --add safe.directory {repo_path} "
            f"    && git fetch -v origin {branch} "
            f"    && git branch {temp_repo_prefix}-{branch} "
            f"        origin/{branch}"
        )

    @task.bash(
        cwd=TEMP_REPOS_DIR,
        trigger_rule="none_failed",
    )
    def git_clone_temp_repo(repo_path: str, branch: str, temp_repo_prefix: str) -> None:
        return (
            "git clone "
            f"    --branch {temp_repo_prefix}-{branch} "
            f"    --single-branch --depth 1 file://{repo_path} "
            f"    {temp_repo_prefix}"
        )

    @task.bash(
        cwd=TEMP_REPOS_DIR,
        trigger_rule="none_failed",
        env={
            "ENTRYPOINT_PARAMS": "{{ params.entrypoint_params }}",
        },
        append_env=True,
    )
    def run_entrypoint(
        temp_repo_prefix: str,
        entrypoint: str,
    ) -> str:
        return (
            "unset GIT_USERNAME && unset GIT_PASSWORD "
            "     && unset AWS_ACCESS_KEY_ID && unset AWS_SECRET_ACCESS_KEY "
            f"    && cd {temp_repo_prefix} && bash -c {entrypoint}"
        )

    @task.bash(
        cwd=TEMP_REPOS_DIR,
        trigger_rule="all_done",
    )
    def remove_temp_repo(temp_repo_prefix: str) -> str:
        return f"[ ! -d {temp_repo_prefix} ] && exit 99 ; " f"rm -r {temp_repo_prefix}"

    @task(trigger_rule="none_failed")
    def capture_dag_run_status() -> None:
        # Have a leaf that fails if its upstream tasks failed,
        # for it to capture failures in upstream tasks as part
        # of the dag run status (upstream failures can get hidden
        # by "all_done" leaf tasks).
        return

    entrypoint_task = run_entrypoint(temp_repo_prefix, entrypoint)

    entrypoint_task >> capture_dag_run_status()

    (
        create_repo_if_needed(repo_uri, repo_path)
        >> git_fetch_at_repo(repo_path, branch)
        >> git_clone_temp_repo(repo_path, branch, temp_repo_prefix)
        >> entrypoint_task
        >> remove_temp_repo(temp_repo_prefix)
    )
