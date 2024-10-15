FROM apache/airflow:2.10.0

RUN pip install PyGitHub apache-airflow-client pathvalidate torch


USER root

RUN apt-get -yy update
RUN apt-get -yy install ca-certificates curl git

# Uncomment for having docker available for the processes in repos.

##### Usual choreography for installing docker.

# RUN for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do sudo apt-get remove $pkg || true; done
#
# RUN install -m 0755 -d /etc/apt/keyrings
# RUN curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
# RUN chmod a+r /etc/apt/keyrings/docker.asc
#
# # Add the repository to Apt sources:
# RUN echo \
#   "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
#   sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
# RUN apt-get update
#
# RUN apt-get install docker-ce-cli docker-buildx-plugin docker-compose-plugin
#

RUN mkdir /home/airflow/temp_repos
RUN chown airflow:0 /home/airflow/temp_repos

USER airflow

COPY ssh_known_hosts /home/airflow/.ssh/known_hosts
COPY gitconfig /home/airflow/.gitconfig
COPY cred_helper.sh /home/airflow/
