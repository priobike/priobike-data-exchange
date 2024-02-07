FROM nginx:1.25-alpine

# Invalidate cache
ARG CACHE_DATE=1970-01-01

WORKDIR /usr/share/nginx/html/
COPY ./static/ ./