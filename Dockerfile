FROM python:3.10

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt

EXPOSE 8089 5557 5558

CMD ["python", "master.py"]
