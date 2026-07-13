FROM python:3.12-slim
RUN useradd --create-home --uid 10001 raven
WORKDIR /workspace
COPY pyproject.toml raven_biocomputer.py app.py ./
RUN pip install --no-cache-dir ".[space]"
RUN mkdir -p /workspace/runs && chown -R raven:raven /workspace
USER raven
ENV GRADIO_SERVER_NAME=0.0.0.0 GRADIO_SERVER_PORT=7860
EXPOSE 7860
CMD ["python", "app.py"]
