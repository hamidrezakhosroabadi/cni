FROM python:3.10.12-bookworm

RUN apt update && apt install bridge-utils iproute2 -y

WORKDIR /application

ADD requirements.txt requirements.txt

ADD *.py ./

ADD templates ./templates

RUN pip install -r requirements.txt

CMD ["python3", "main.py"]