FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgtk-3-0 \
    libasound2 \
    libdbus-glib-1-2 \
    libx11-xcb1 \
    libxtst6 \
    libnss3 \
    libxss1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Installe tes dépendances Python
COPY env/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Pré-télécharge le binaire Camoufox dans l'image
RUN camoufox fetch

# Copie le reste de ton projet
COPY . .

ENV MY_APP_EMAIL=""
ENV MY_APP_PASSWORD=""

CMD ["python", "script.py"]