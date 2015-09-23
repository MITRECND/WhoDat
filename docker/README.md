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
To deploy the pyDat web frontend you can run the following command which will daemonize and run in the background:

```bash
$ docker run -d -p 80:80 -v /path/to/custom_settings.py:/pydat/custom_settings.py --name pydat-server mitrecnd/pydat
```

As with any docker image, if you want the image to auto restart on some failure condition you can set the '--restart' flag to 'on-failure' or 'always'.

Note that you will still need to create and pass in a custom_setings.py configuration file to properly configure pyDat so it can access the backend data store.


Image Organization
------------------

This image is based on Apache's httpd image with all required dependencies to use pyDat with MongoDB or ElasticSearch. 

The repo has been installed into /opt/WhoDat but a soft link has been created at /pydat which points to /opt/WhoDat/pydat/pydat to make it easier to add a custom_settings file. 

The PATH has also been modified to include the scripts directory allowing you to directly execute the populate scripts from the command line:

```
$ docker run --rm -it -v /path/to/whois/files:/whois mitrecnd/pydat elasticsearch_populate.py  -d /whois -i 1 -o "First Import" -u es:9200
```

If you're hosting an elasticsearch node via docker, you can use docker's link feature to allow the pydat docker image to access your deployed elasticsearch node:

```
$ docker run --rm -it --link elasticsearch-node:es -v /path/to/whois/files:/whois mitrecnd/pydat elasticsearch_populate.py  -d /whois -i 1 -o "First Import" -u es:9200
```
