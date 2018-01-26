FROM oarmeta/ejsonschema

RUN apt-get update && apt-get install zip

COPY entrypoint.sh /root/entrypoint.sh

RUN mkdir -p /dev/oar-metadata
WORKDIR /dev/oar-metadata

ENV MONGO_TESTDB_URL mongodb://localhost/testdb
ENV PYTHONPATH /dev/oar-metadata/python

ENTRYPOINT ["/root/entrypoint.sh"]
