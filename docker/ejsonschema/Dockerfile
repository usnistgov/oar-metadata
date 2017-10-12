FROM oarmeta/jq:latest

RUN apt-get update && apt-get install -y python python-pip python-dev unzip \
                                         uwsgi uwsgi-plugin-python python-yaml
RUN pip install json-spec jsonschema requests pynoid filelock

WORKDIR /root
RUN curl -L -o jsonmerge.zip \
    https://github.com/RayPlante/jsonmerge/archive/oar.zip && \
    unzip jsonmerge.zip && \
    cd jsonmerge-oar && \
    python setup.py install

RUN curl -L -o ejsonschema.zip \
    https://github.com/usnistgov/ejsonschema/archive/master.zip && \
    unzip ejsonschema.zip && \
    cd ejsonschema-master && \
    python setup.py install

CMD ["bash"]

