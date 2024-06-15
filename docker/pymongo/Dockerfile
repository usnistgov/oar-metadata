# This provides the base support for Python 3.8 and MongoDB 4.4 

FROM ubuntu:focal
# VOLUME /data
MAINTAINER Ray Plante <raymond.plante@nist.gov>
COPY mongod.conf /etc/mongod.conf
COPY mongod_ctl.sh /usr/local/bin

# Set the timezone to stop tcaza package from hanging
ENV TZ=America/New_York
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update && apt-get install -y gnupg curl

# Add the MongoDB GPG key
RUN curl -fsSL https://www.mongodb.org/static/pgp/server-4.4.asc | apt-key add -

# Add MongoDB repository
RUN echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/4.4 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-4.4.list
    
RUN apt-get update && apt-get install -y ca-certificates locales python3.8 python3-pip python3.8-dev

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.8 1; \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 1; \
    update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1
RUN locale-gen en_US.UTF-8

COPY cacerts/README.md cacerts/*.crt /usr/local/share/ca-certificates/
RUN update-ca-certificates
ENV REQUESTS_CA_BUNDLE /etc/ssl/certs/ca-certificates.crt

ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8
RUN python -m pip install pymongo
