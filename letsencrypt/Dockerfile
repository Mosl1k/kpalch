FROM nginx


RUN apt-get update && \
    apt-get install -y certbot #&& \
#    certbot certonly --webroot -w /var/www/html -d geshtalt.ddns.net -d www.geshtalt.ddns.net && \
#    ln -s /etc/letsencrypt/live/geshtalt.ddns.net/fullchain.pem /etc/nginx/certs/cert.pem && \
#    ln -s /etc/letsencrypt/live/geshtalt.ddns.net/privkey.pem /etc/nginx/certs/key.pem


COPY ./nginx/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 443
