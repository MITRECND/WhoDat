# Stage 1 - Build Frontend
FROM node:lts AS FRONTEND
WORKDIR /opt/pydat
COPY frontend /opt/pydat/frontend
ENV GENERATE_SOURCEMAP=false
RUN \
  cd frontend && \
  npm install && \
  npm run build:isolated


# Stage 2 - Python Backend plus compiled frontend assets
FROM python:3.8-alpine
COPY backend /tmp/pydat/backend
COPY entry.sh /

RUN \
    mkdir /opt/pydat && \
    cd /opt/pydat && \
    python3 -m venv pydat-env && \
    /opt/pydat/pydat-env/bin/pip install gunicorn && \
    cd /tmp/pydat && \
    /opt/pydat/pydat-env/bin/pip install ./backend && \
    touch /opt/pydat/config.py

COPY --from=FRONTEND /opt/pydat/frontend/build /opt/pydat/ui

WORKDIR /opt/pydat

CMD /entry.sh