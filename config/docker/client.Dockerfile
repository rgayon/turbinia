FROM ubuntu:bionic

RUN apt -y update
RUN apt -y upgrade

RUN apt -y install python-pip

RUN pip install turbinia
