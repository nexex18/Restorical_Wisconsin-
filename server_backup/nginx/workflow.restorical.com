# Nginx configuration for workflow.restorical.com
# n8n Workflow Automation Platform
# Created: 2025-10-09

server {
    server_name workflow.restorical.com;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Note: We are NOT adding nginx basic auth here
    # n8n has its own authentication (configured in .env)
    
    # ========================================
    # n8n Application (root path)
    # ========================================
    
    location / {
        proxy_pass http://127.0.0.1:5678/;
        proxy_http_version 1.1;
        
        # WebSocket support (critical for n8n)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Standard headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
        
        # Disable buffering for real-time updates
        proxy_buffering off;
        proxy_cache_bypass $http_upgrade;
        
        # Extended timeouts for long-running workflows
        proxy_connect_timeout 3600s;
        proxy_send_timeout 3600s;
        proxy_read_timeout 3600s;
    }

    listen [::]:443 ssl; # managed by Certbot
    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/workflow.restorical.com/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/workflow.restorical.com/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot

}


server {
    if ($host = workflow.restorical.com) {
        return 301 https://$host$request_uri;
    } # managed by Certbot


    listen 80;
    listen [::]:80;
    server_name workflow.restorical.com;
    return 404; # managed by Certbot


}