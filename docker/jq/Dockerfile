From oar-metadata/pymongo

RUN apt-get update && \
    apt-get install -y curl 

WORKDIR /root

# Download a jq binary and do a checksum check on it
COPY jq-linux-amd64.sha256 jq-linux-arm64.sha256 ./
RUN arch=$(uname -m) && \
    { [ "$arch" != "x86_64" ] || arch="amd64"; [ "$arch" != "aarch64" ] || arch="arm64"; } && \
    curl -L -o jq-linux-$arch \
    https://github.com/stedolan/jq/releases/download/jq-1.7.1/jq-linux-$arch && \
    sha256sum -c jq-linux-$arch.sha256

# install jq
RUN arch=$(uname -m) && \
    { [ "$arch" != "x86_64" ] || arch="amd64"; [ "$arch" != "aarch64" ] || arch="arm64"; } && \
    chmod a+x jq-linux-$arch && cp jq-linux-$arch /usr/local/bin/jq

CMD ["bash"]




