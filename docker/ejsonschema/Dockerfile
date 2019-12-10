FROM oar-metadata/jq:latest

RUN apt-get update && apt-get install -y unzip uwsgi uwsgi-plugin-python3 
RUN update-alternatives --install /usr/lib/uwsgi/plugins/python_plugin.so \
    python_plugin.so /usr/lib/uwsgi/plugins/python3_plugin.so 1

RUN pip install setuptools --upgrade
RUN pip install json-spec jsonmerge==1.3.0 jsonschema==2.6.0 requests \
                pytest==4.6.5 filelock crossrefapi pyyaml

WORKDIR /root

RUN curl -L -o ejsonschema.zip \
    https://github.com/usnistgov/ejsonschema/archive/master.zip && \
    unzip ejsonschema.zip && \
    cd ejsonschema-master && \
    python setup.py install

RUN curl -L -o pynoid.zip \
    https://github.com/RayPlante/pynoid/archive/master.zip && \
    unzip pynoid.zip && \
    cd pynoid-master && \
    python setup.py install

CMD ["bash"]

