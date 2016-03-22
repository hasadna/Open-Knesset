FROM ubuntu:14.04
MAINTAINER Doody Parizada <doody.parizada @ gmail.com>

# install apt dependencies
RUN apt-get update -y && \
    apt-get install -y build-essential git python python-dev python-setuptools python-pip && \
    apt-get build-dep -y python-imaging python-lxml && \
    pip install --upgrade pip && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN mkdir -p /opt/knesset /opt/database

# download database file into database location
WORKDIR /opt/database
RUN apt-get install -y wget && \
    wget http://oknesset-devdb.s3.amazonaws.com/dev.db.bz2 && \
    bzip2 -d dev.db.bz2 && \
    apt-get purge -y --auto-remove wget

# install python requirements
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

VOLUME ["/opt/knesset"]
WORKDIR /opt/knesset
EXPOSE 8000

# set up entry point and default command
COPY docker/entrypoint.sh /tmp/entrypoint.sh
ENTRYPOINT ["/tmp/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
