FROM python:3.11-slim

# Sistem bağımlılıkları ve FFmpeg kurulumu
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    curl \
    unzip \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

# Google Fonts (Inter, Montserrat, Cinzel, Bebas Neue, Anton, Poppins, Outfit) - Yerel font varlıklarından
RUN mkdir -p /usr/share/fonts/truetype/custom
COPY assets/fonts/*.ttf /usr/share/fonts/truetype/custom/
RUN fc-cache -f -v

WORKDIR /app

# Pip bağımlılıkları
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodları ve statik fontlar
COPY . .

# Geçici indirme ve render dizinleri
RUN mkdir -p /app/temp /app/logs /app/assets/fonts

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
