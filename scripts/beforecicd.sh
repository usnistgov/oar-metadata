#!/bin/bash
sudo rm -r /opt/data/backup/oar-metadata/*
if [ -f /home/ubuntu/oar-docker/rmm/ingest/pdr-nerdm.zip ];
then
  #backup previous build
  sudo cp -r /home/ubuntu/oar-docker/rmm/ingest/pdr-nerdm.zip /opt/data/backup/oar-metadata
  #remove previous build
  sudo rm -r /home/ubuntu/oar-docker/rmm/ingest/pdr-nerdm.zip
fi
