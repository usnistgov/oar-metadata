FROM oar-metadata/jq

RUN apt-get update && apt-get install -y unzip uuid-dev libcap-dev \
                                         libpcre3-dev python3-distutils

RUN python -m pip install "setuptools<66.0.0" 
RUN python -m pip install lxml uwsgi json-spec jsonschema==2.4.0 requests \
                          pytest==4.6.5 filelock crossrefapi pyyaml jsonpath_ng
RUN python -m pip install --no-dependencies jsonmerge==1.3.0 

WORKDIR /root

RUN curl -L -o ejsonschema.zip \
    https://github.com/usnistgov/ejsonschema/archive/1.0rc4.zip && \
    unzip ejsonschema.zip && \
    cd ejsonschema-1.0rc4 && \
    python setup.py install --install-purelib=/usr/local/lib/python3.10/dist-packages

RUN curl -L -o pynoid.zip \
    https://github.com/RayPlante/pynoid/archive/master.zip && \
    unzip pynoid.zip && \
    cd pynoid-master && \
    python setup.py install --install-purelib=/usr/local/lib/python3.10/dist-packages

CMD ["bash"]

