FROM oar-metadata/ejsonschema

RUN apt-get update && apt-get install -y zip wget git

ENV GOSU_VERSION 1.10
RUN set -ex; \
    arch="$(dpkg --print-architecture | awk -F- '{ print $NF }')"; \
    wget -O /usr/local/bin/gosu \
   "https://github.com/tianon/gosu/releases/download/$GOSU_VERSION/gosu-$arch"; \
    wget -O /usr/local/bin/gosu.asc \
"https://github.com/tianon/gosu/releases/download/$GOSU_VERSION/gosu-$arch.asc";\
    export GNUPGHOME="$(mktemp -d)"; \
    gpg --keyserver ha.pool.sks-keyservers.net \
         --recv-keys B42F6819007F00F88E364FD4036A9C25BF357DD4; \
    gpg --batch --verify /usr/local/bin/gosu.asc /usr/local/bin/gosu; \
    rm -r "$GNUPGHOME" /usr/local/bin/gosu.asc; \
    chmod +x /usr/local/bin/gosu; \
    gosu nobody true

# Create the user that build/test operations should run as.  Normally,
# this is set to match identity information of the host user that is
# launching the container.
#
RUN sed --in-place -e '/CREATE_MAIL_SPOOL/ s/=yes/=no/' /etc/default/useradd
ARG devuser=developer
ARG devuid=1000
RUN grep -qs :${devuid}: /etc/group || \
    groupadd --gid $devuid $devuser
RUN grep -Pqs ":${devuid}:\d+:" /etc/passwd || \
    useradd -m --comment "OAR Developer" --shell /bin/bash \
            --gid $devuid --uid $devuid $devuser

ENV MONGO_TESTDB_URL mongodb://localhost/testdb
ENV PYTHONPATH /dev/oar-metadata/python

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod a+rx /usr/local/bin/entrypoint.sh
COPY mdtests.sh /usr/local/bin/mdtests.sh
RUN chmod a+rx /usr/local/bin/mdtests.sh

VOLUME /dev/oar-metadata
VOLUME /app/dist

RUN mkdir -p /dev/oar-metadata
WORKDIR /dev/oar-metadata

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
