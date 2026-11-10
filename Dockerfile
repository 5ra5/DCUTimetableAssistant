FROM python:3.12-slim

WORKDIR /app

COPY ./requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY ./backend ./backend
COPY ./frontend ./frontend
COPY ./scripts ./scripts
COPY ./data ./data

RUN python3 scripts/init_db.py

EXPOSE 8080

CMD [ "uvicorn", "backend.app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8080" ]
