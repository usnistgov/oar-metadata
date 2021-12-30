From oar-metadata/pymongo

RUN apt-get update && \
    apt-get install -y libonig-dev curl build-essential libtool zip \
                       unzip autoconf git
RUN pip install pipenv

WORKDIR /root
RUN git clone http://github.com/stedolan/jq.git jq-dev && \
    cd jq-dev && \
    git checkout a9f97e9e61a910a374a5d768244e8ad63f407d3e && \
    git submodule update --init && \
    autoreconf -fi && \
    (cd docs && pipenv install) && \
    ./configure --with-oniguruma=builtin && \
    make -j8 && \
    make check && \
    make install

CMD ["bash"]




