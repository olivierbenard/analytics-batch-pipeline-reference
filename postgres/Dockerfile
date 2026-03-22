FROM postgres:15-alpine

RUN apk add --no-cache curl bash postgresql-client

ENV POSTGRES_INITDB_ARGS="--encoding=UTF8 --locale=C"

EXPOSE 5432

HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD pg_isready -U $POSTGRES_USER