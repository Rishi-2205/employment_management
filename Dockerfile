from python:3.11-slim
WORKDIR /app

copy ./backend ./backend
copy ./frontend ./frontend

copy backend/requirements.txt .
run pip install --no-cache-dir -r requirements.txt

EXPOSE 8086

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8086", "--reload"]