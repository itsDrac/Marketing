FROM python:3.11-alpine

WORKDIR /code

COPY ./requirements.txt ./requirements.txt

RUN pip install --no-cache-dir --upgrade -r ./requirements.txt

COPY . .

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0", "app:create_app()"]
