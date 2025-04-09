FROM nginx:1.25-alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom configuration
COPY chessmate.conf /etc/nginx/conf.d/

# Create required directories
RUN mkdir -p /app/chess_mate/staticfiles && \
    mkdir -p /app/chess_mate/media && \
    mkdir -p /app/chess_mate/frontend/build && \
    mkdir -p /etc/letsencrypt && \
    mkdir -p /var/www/certbot && \
    chown -R nginx:nginx /etc/letsencrypt && \
    chown -R nginx:nginx /var/www/certbot

EXPOSE 80
EXPOSE 443

CMD ["nginx", "-g", "daemon off;"]
