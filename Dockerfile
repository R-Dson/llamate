# Define build arguments for target platform (defaults to current build platform)
ARG TARGETOS=linux
ARG TARGETARCH=amd64

# Builder stage: build the llamate binary
FROM python:3.11-slim-bullseye AS builder

# Set environment variables to reflect the target platform
ENV TARGETOS=${TARGETOS}
ENV TARGETARCH=${TARGETARCH}

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

# Build binary
RUN pyinstaller llamate.spec

# Runtime stage: run the server
FROM debian:bullseye-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libssl1.1 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV MODEL_DIR=/app/models
ENV PORT=11434
ENV LLAMATE_HOME=/app

# Create directory structure
RUN mkdir -p ${MODEL_DIR} ${LLAMATE_HOME}/bin

# Copy built binary
COPY --from=builder /app/dist/llamate /app/llamate

# Initialize llamate to download the llama-swap binary
RUN /app/llamate init

# Expose port
EXPOSE ${PORT}

# Set entrypoint
ENTRYPOINT ["/app/llamate", "serve", "--port", "11434", "--public"]