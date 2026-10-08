FROM python:3.12-slim

WORKDIR /tool
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir .

WORKDIR /workspace
ENTRYPOINT ["pytest-evidence"]

