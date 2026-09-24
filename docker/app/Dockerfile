FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py test_inventory.py ./
# Scanner library is served by the app itself, so the phone does not depend on
# a CDN being reachable during a demo (see evidence/decision-table.md, P3).
COPY static/ ./static/

VOLUME /data

EXPOSE 5000

CMD ["python", "app.py"]
