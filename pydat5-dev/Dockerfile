# Stage 1 - Build Frontend
FROM node:lts AS FRONTEND
WORKDIR /opt/pydat
COPY . /opt/pydat/

RUN \
 echo "GENERATE_SOURCEMAP=false" > .env && \
 cd frontend && \
   npm install && \
   npm run build:isolated


# Stage 2 - Python Backend plus compiled frontend assets
FROM python:3.6-alpine AS BACKEND
COPY . /tmp/pydat/
COPY entry.sh /
ARG ESVERSION=7

RUN \
    mkdir /opt/pydat && \
    cd /opt/pydat && \
    python3 -m venv pydat-env && \
    /opt/pydat/pydat-env/bin/pip install gunicorn && \
    if [ "${ESVERSION}" = "6" ]; then /opt/pydat/pydat-env/bin/pip install 'elasticsearch>=6.0.0,<7.0.0'; fi && \
    cd /tmp/pydat && \
    /opt/pydat/pydat-env/bin/pip install ./backend && \
    touch /opt/pydat/config.py

COPY --from=FRONTEND /opt/pydat/frontend/build /opt/pydat/ui

WORKDIR /opt/pydat

CMD /entry.sh