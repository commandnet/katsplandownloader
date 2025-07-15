FROM python:3.6.12-alpine3.12
COPY . /opt/
WORKDIR /opt/
RUN pip install -r requirements.txt
CMD ["python3", "main.py"]