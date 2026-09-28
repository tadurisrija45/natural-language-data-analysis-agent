FROM python:3.11-slim

# Prevent writing bytecode and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /sandbox

# Install minimal needed data libraries
RUN pip install --no-cache-dir \
    pandas==2.2.2 \
    numpy==1.26.4 \
    scipy==1.13.0 \
    openpyxl==3.1.2 \
    pyarrow==16.0.0

# Create unprivileged runner user
RUN useradd -m -u 10001 sandboxuser && \
    chown -R sandboxuser:sandboxuser /sandbox

USER sandboxuser

ENTRYPOINT ["python", "/sandbox/sandbox_runner.py"]
