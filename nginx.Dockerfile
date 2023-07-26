FROM nginx:1.25.1

RUN mkdir -p /usr/nginx && \
    openssl req -x509 -newkey rsa:2042 -keyout /usr/nginx/ssl.key \
                -sha256 -days 365 -nodes -subj "/CN=localhost" \
                -out /usr/nginx/ssl.crt
