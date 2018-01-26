#!/bin/bash
APP_DIR=/home/ubuntu/oar-docker/apps
DOCKER_CONTAINER_NAME=rmm-ingest
cd $APP_DIR

if [[ $(sudo docker ps -aqf "name=$DOCKER_CONTAINER_NAME") ]]; then
    sudo docker rm -f $(sudo docker ps -aqf "name=$DOCKER_CONTAINER_NAME")
fi
if [[ $(sudo docker images $DOCKER_CONTAINER_NAME -aq) ]]; then
   sudo docker rmi -f $(sudo docker images $DOCKER_CONTAINER_NAME -aq)
fi

sudo docker-compose rm -f
[ -e "${APP_DIR}/rmm/mongod/db" ] && sudo rm -rf ${APP_DIR}/rmm/mongod/db
sudo docker-compose build --no-cache
sudo docker-compose up -d

