FROM python:3.12-slim-bookworm

RUN sed -i 's@http://deb.debian.org@https://deb.debian.org@g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends bash libreoffice-calc \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir openpyxl==3.1.5

WORKDIR /workspace
COPY input.xlsx /workspace/input.xlsx
CMD ["sleep", "infinity"]
