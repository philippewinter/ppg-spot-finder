# PPG Spot Finder — static single-page app served by nginx
FROM nginx:alpine

# Serve the app as the site index
COPY PPG-Spot-Finder.html /usr/share/nginx/html/index.html

# gzip + cache config (the file is ~2.2 MB raw, ~650 KB gzipped)
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
