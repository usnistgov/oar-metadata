FROM mongo:3.6
# VOLUME /data
MAINTAINER Ray Plante <raymond.plante@nist.gov>
COPY mongod.conf /etc/mongod.conf
COPY mongod_ctl.sh /usr/local/bin

RUN apt-get update && apt-get install -y locales python3 python3-pip python3-dev
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1; \
    update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1
RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8
RUN pip install pymongo

