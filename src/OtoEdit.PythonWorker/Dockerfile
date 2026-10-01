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

# Google Fonts (Inter ve Montserrat) kurulumu - GitHub Releases Üzerinden
RUN mkdir -p /usr/share/fonts/truetype/custom && \
    curl -sL "https://github.com/rsms/inter/releases/download/v3.19/Inter-3.19.zip" -o inter.zip && \
    unzip -o inter.zip -d inter_fonts && \
    cp -r inter_fonts/Inter\ Desktop/*.ttf /usr/share/fonts/truetype/custom/ || cp inter_fonts/*.ttf /usr/share/fonts/truetype/custom/ || true && \
    rm -rf inter.zip inter_fonts && \
    curl -sL "https://github.com/JulietaUla/Montserrat/archive/refs/heads/master.zip" -o montserrat.zip && \
    unzip -o montserrat.zip -d mont_fonts && \
    cp mont_fonts/Montserrat-master/fonts/ttf/*.ttf /usr/share/fonts/truetype/custom/ || true && \
    rm -rf montserrat.zip mont_fonts && \
    curl -sL "https://fonts.google.com/download?family=Cinzel" -o cinzel.zip && \
    unzip -o cinzel.zip -d /usr/share/fonts/truetype/custom/ || true && \
    rm -rf cinzel.zip && \
    fc-cache -f -v

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
