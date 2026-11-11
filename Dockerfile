FROM python:3.12-slim

WORKDIR /app

COPY ./requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY ./backend ./backend
COPY ./frontend ./frontend
COPY ./scripts ./scripts
COPY ./data ./data

EXPOSE 8080

# init_db.py runs on EVERY start (it is safe to repeat: it only inserts or updates). It cannot run at build
# time, because compose mounts ./data over /app/data and would hide a database built into the image.
# One uvicorn worker only (a background refresher added later must start once). No --reload in the image.
CMD ["sh", "-c", "python scripts/init_db.py && exec uvicorn backend.app.main:app --host 0.0.0.0 --port 8080"]
