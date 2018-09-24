FROM httpd:2.4

LABEL maintainer="mitrecnd, http://github.com/mitrecnd"

ARG ES_VERSION=5
ARG WSGI_VERSION="4.6.4"

ENV PATH=$PATH:/opt/WhoDat/pydat/scripts

COPY . /opt/WhoDat/
ADD https://bootstrap.pypa.io/get-pip.py /tmp/
ADD https://github.com/GrahamDumpleton/mod_wsgi/archive/${WSGI_VERSION}.tar.gz /tmp/

RUN \
    chmod +x /tmp/get-pip.py && \
    buildDeps='apt-utils \
               autoconf \
               automake \
               build-essential \
               libapr1-dev \
               libaprutil1-dev' \
    set -x && \
    apt-get -q update && \
    apt-get install -y python python-dev $buildDeps && \
    /tmp/get-pip.py && \
    rm /tmp/get-pip.py && \
    pip install -r /opt/WhoDat/requirements.es${ES_VERSION}.txt && \
    cd /tmp/ && \
    tar -zxf ${WSGI_VERSION}.tar.gz && \
    rm ${WSGI_VERSION}.tar.gz && \
    cd /tmp/mod_wsgi-${WSGI_VERSION} && \
    ./configure --prefix=${HTTPD_PREFIX} && \
    make && \
    make install && \
    rm -r /tmp/mod_wsgi-${WSGI_VERSION} && \
    cp /opt/WhoDat/docker/apache.config /usr/local/apache2/conf/httpd.conf && \
    ln -s /opt/WhoDat/pydat/pydat/ /pydat  && \
    apt-get autoremove --purge -y $buildDeps && \
    rm -r /var/lib/apt/lists/*
