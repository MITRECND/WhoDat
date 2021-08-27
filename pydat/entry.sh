#!/bin/sh

. /opt/pydat/pydat-env/bin/activate

export PYDAT_STATICFOLDER="/opt/pydat/ui"
export PYDATCONFIG="/opt/pydat/config.py"

if [[ -z "${WORKERS}" ]]; then
    WORKERS=4
fi

if [[ -z "${HOST}" ]]; then
    HOST="0.0.0.0:8888"
fi

gunicorn -w ${WORKERS} -b ${HOST} "pydat.api:create_app()"