# syntax=docker/dockerfile:1
# The demo container: pumllint from this repository's source, plus the page
# generator. pumllint is pure Python with no dependencies, so it is copied in
# rather than pip-installed: the build needs no package index, only the base
# image. Built by compose.yaml with the repository root as context;
# Dockerfile.dockerignore keeps that context down to the files needed.
FROM python:3.12-slim

COPY pumllint /opt/pumllint/pumllint
WORKDIR /demo
COPY sandbox/credit-application/demo_site.py /demo/
# diagrams/ is mounted from the host (compose.yaml), so edits show up on reload
ENV PYTHONPATH=/opt/pumllint DEMO_OUT=/tmp/demo-out PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "demo_site.py", "serve", "--port", "8000"]
