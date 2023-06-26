FROM python:3.9 AS builder

# Invalidate cache
ARG CACHE_DATE=1970-01-01

COPY ./create_exchange_jsons.py ./

# In the future, we need to remove this line because then we don't want to serve the example files but instead the files created by "create_exchange_jsons.py"
COPY ./static ./static

RUN python create_exchange_jsons.py

FROM nginx AS runner

WORKDIR /usr/share/nginx/html/
COPY --from=builder ./static/ ./