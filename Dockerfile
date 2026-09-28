FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgtk-3-0 \
    libasound2 \
    libdbus-glib-1-2 \
    libx11-xcb1 \
    libxtst6 \
    libnss3 \
    libxss1 \
    xvfb \
    xauth \
    curl \
    x11vnc \
    novnc \
    websockify \
    && rm -rf /var/lib/apt/lists/*

COPY ./env/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN camoufox fetch

COPY ./app /app

ENV PYTHONUNBUFFERED=1

EXPOSE 6080

# Script pour lancer Xvfb, VNC, noVNC puis le script Python
CMD xvfb-run --auto-servernum --server-args="-screen 0 1920x1080x24" sh -c "\
    x11vnc -forever -shared -rfbport 5900 -display \$DISPLAY & \
    websockify --web=/usr/share/novnc/ 6080 localhost:5900 & \
    python -u /app/main.py"