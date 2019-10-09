FROM oar-metadata/jq:latest

RUN apt-get update && apt-get install -y python python-pip python-dev unzip \
                                         uwsgi uwsgi-plugin-python python-yaml
RUN pip install setuptools --upgrade
RUN pip install json-spec jsonmerge==1.3.0 jsonschema==2.6.0 requests pynoid \
                pytest==4.6.5 filelock crossrefapi

WORKDIR /root

RUN curl -L -o ejsonschema.zip \
    https://github.com/usnistgov/ejsonschema/archive/master.zip && \
    unzip ejsonschema.zip && \
    cd ejsonschema-master && \
    python setup.py install

CMD ["bash"]

