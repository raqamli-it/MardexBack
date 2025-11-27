# Base image
FROM python:3.10

# Working directory
WORKDIR /Mardex

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    proj-bin \
    proj-data \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /Mardex/
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy wait-for-it script
COPY wait-for-it.sh /Mardex/wait-for-it.sh
RUN chmod +x /Mardex/wait-for-it.sh

# Create and set permissions for staticfiles folder
RUN mkdir -p /Mardex/staticfiles
RUN chmod 755 /Mardex/staticfiles

# Copy project files
COPY . /Mardex/

# Django settings
ENV DJANGO_SETTINGS_MODULE=config.settings

# Expose port
EXPOSE 8000

# Command
CMD ["sh", "-c", "./wait-for-it.sh mardex_db:5432 -- python manage.py migrate && python manage.py collectstatic --noinput && daphne -b 0.0.0.0 -p 8000 config.asgi:application"]
