# Builder stage: build the llamate binary
FROM python:3.11-slim-bullseye AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    zlib1g-dev \
    libssl-dev \
    upx \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    pyyaml \
    huggingface-hub \
    click \
    requests \
    certifi \
    pyinstaller

# Create a placeholder VERSION file for PyInstaller
RUN echo "0.0.0" > VERSION

# Build binary
RUN pyinstaller llamate.spec

# Runtime stage: run the server
FROM debian:bullseye-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libssl1.1 \
    ca-certificates \
    pciutils \
    usbutils \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PORT=11434
ENV LLAMATE_HOME=/app

# Copy built binary
COPY --from=builder /app/dist/llamate /usr/local/bin/llamate

# Expose port
EXPOSE ${PORT}

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
RUN mkdir -p /root/.config && ln -s /app /root/.config/llamate

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["serve", "--port", "11434"]