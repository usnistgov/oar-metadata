FROM mongo:4.2
# VOLUME /data
MAINTAINER Ray Plante <raymond.plante@nist.gov>
COPY mongod.conf /etc/mongod.conf
COPY mongod_ctl.sh /usr/local/bin

RUN sed -e '/jessie-updates/ s/^deb/#deb/' /etc/apt/sources.list \
    > /tmp/sources.list && mv /tmp/sources.list /etc/apt/sources.list
RUN apt-get update && apt-get install -y python python-pip python-dev
RUN pip install pymongo

