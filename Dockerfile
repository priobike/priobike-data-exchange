ARG ENVIRONMENT=release

FROM bikenow.vkw.tu-dresden.de/priobike/priobike-nginx:${ENVIRONMENT}

# Invalidate cache
ARG CACHE_DATE=1970-01-01

WORKDIR /usr/share/nginx/html/
COPY ./static/ ./