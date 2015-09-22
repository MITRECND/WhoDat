pyDat Docker Image
==================

This is the configuration dirctory for the Docker image of [pyDat](https://github.com/MITRECND/WhoDat) for [Docker](https://www.docker.io/)'s [trusted build](https://index.docker.io/u/mitrecnd/pydat/) published to the public [Docker Registry](https://index.docker.io/).

### Base Docker Image
* [httpd:2.4](https://index.docker.io/_/httpd/)

### Image Size
[![](https://badge.imagelayers.io/mitrecnd/pydat:latest.svg)](https://imagelayers.io/?images=mitrecnd/pydat:latest 'Get your own badge on imagelayers.io')

### Image Tags
```bash
$ docker images

REPOSITORY          TAG                 IMAGE ID           VIRTUAL SIZE
mitrecnd/pydat      latest              d06aed897778       295.6 MB
```

### Installation

1. Install [Docker](https://www.docker.io/).

2. Download [trusted build](https://index.docker.io/u/mitrecnd/pydat/) from public [Docker Registry](https://index.docker.io/): `docker pull mitrecnd/pydat`

#### Alternatively, build an image from the Dockerfile
```bash
$ docker build -t mitrecnd/pydat github.com/mitrecnd/WhoDat
```

### Usage
```bash
$ docker run -d -p 80:80 -v /path/to/custom_settings.py:/opt/WhoDat/pydat/pydat/custom_settings.py --name pydat-server mitrecnd/pydat
```

Note that you will still need to create and pass in a custom_setings.py configuration file to properly configure pyDat.
