FROM nginx:1.29.0-alpine

EXPOSE 8080

COPY ./nginx/error_pages/ /etc/nginx/html/error_pages/

COPY ./nginx/nginx.conf.template /etc/nginx/templates/default.conf.template