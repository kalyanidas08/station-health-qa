# Built with context set to the repo root (see docker-compose.test.yml),
# because pytest.ini's `pythonpath = ../service` expects service/ to be a
# sibling directory - a build context scoped to qa-automation-suite/ alone
# couldn't COPY anything from outside it.
FROM python:3.11-slim

WORKDIR /workspace

COPY service/ ./service/
COPY qa-automation-suite/ ./qa-automation-suite/

WORKDIR /workspace/qa-automation-suite

RUN pip install --no-cache-dir -r requirements-test.txt

CMD ["pytest", "-v"]
