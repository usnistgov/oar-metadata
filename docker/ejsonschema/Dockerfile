FROM oar-metadata/jqfromsrc:latest

RUN apt-get update && apt-get install -y unzip uwsgi uwsgi-src \
                                         uuid-dev libcap-dev libpcre3-dev python3-distutils
RUN PYTHON=python3.8 uwsgi --build-plugin "/usr/src/uwsgi/plugins/python python38" && \
    mv python38_plugin.so /usr/lib/uwsgi/plugins/python38_plugin.so && \
    chmod 644 /usr/lib/uwsgi/plugins/python38_plugin.so

RUN update-alternatives --install /usr/lib/uwsgi/plugins/python3_plugin.so \
    python_plugin.so /usr/lib/uwsgi/plugins/python38_plugin.so 1

RUN python -m pip install "setuptools<66.0.0"
RUN python -m pip install json-spec jsonschema==2.4.0 requests \
                          pytest==4.6.5 filelock crossrefapi pyyaml jsonpath_ng
RUN python -m pip install --no-dependencies jsonmerge==1.3.0 

WORKDIR /root

RUN curl -L -o ejsonschema.zip \
    https://github.com/usnistgov/ejsonschema/archive/master.zip && \
    unzip ejsonschema.zip && \
    cd ejsonschema-master && \
    python setup.py install --install-purelib=/usr/local/lib/python3.8/dist-packages

RUN curl -L -o pynoid.zip \
    https://github.com/RayPlante/pynoid/archive/master.zip && \
    unzip pynoid.zip && \
    cd pynoid-master && \
    python setup.py install --install-purelib=/usr/local/lib/python3.8/dist-packages

CMD ["bash"]

