From oar-metadata/pymongo

RUN apt-get update && \
    apt-get install -y libonig-dev curl build-essential libtool zip \
                       unzip autoconf git

WORKDIR /root
RUN git clone http://github.com/stedolan/jq.git jq-dev && \
    cd jq-dev && \
    git checkout 6306ac89667cf35f47ddc40aa0630546c57e387f && \
    git submodule update --init && \
    autoreconf -fi && \
    ./configure --with-oniguruma=builtin && \
    make -j8 && \
    make check && \
    make install

CMD ["bash"]




