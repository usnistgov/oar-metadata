From oar-metadata/pymongo

RUN apt-get update && \
    apt-get install -y libonig-dev curl build-essential libtool zip \
                       unzip autoconf git python3 pipenv

WORKDIR /root
RUN git clone http://github.com/stedolan/jq.git jq-dev && \
    cd jq-dev && \
    git checkout 80052e5275ae8c45b20411eecdd49c945a64a412 && \
    git submodule update --init && \
    autoreconf -fi && \
    ./configure --with-oniguruma=builtin && \
    make -j8 && \
    make check && \
    make install

CMD ["bash"]




