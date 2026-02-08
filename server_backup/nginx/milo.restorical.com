# Nginx configuration for milo.restorical.com subdomain
# Created: 2025-10-09
# Updated: 2026-02-03 - Replaced basic auth with OAuth2 Proxy (Microsoft 365 SSO)
# Purpose: Provide clean domain-based access to Streamlit, FastHTML apps, and static content

server {
    server_name milo.restorical.com;
    
    # Allow large file uploads (for ZipHandling)
    client_max_body_size 2G;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # ========================================
    # OAuth2 Proxy Endpoints
    # ========================================
    
    location /oauth2/ {
        proxy_pass http://127.0.0.1:4180;
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location = /oauth2/auth {
        proxy_pass http://127.0.0.1:4180;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_pass_request_body off;
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
        proxy_set_header Content-Length "";
    }

    # ========================================
    # Streamlit Application (with /streamlit/ path)
    # ========================================
    
    location = /streamlit {
        return 301 /streamlit/;
    }
    
    location /streamlit/ {
        auth_request /oauth2/auth;
        error_page 401 = /oauth2/sign_in;
        auth_request_set $user $upstream_http_x_auth_request_user;
        proxy_set_header X-User $user;

        proxy_pass http://127.0.0.1:8501/;
        proxy_http_version 1.1;
        
        # WebSocket support for Streamlit
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
        
        # Long timeout for Streamlit sessions
        proxy_read_timeout 86400;
    }
    
    # ========================================
    # FastHTML Application
    # ========================================
    
    location = /fasthtml {
        return 301 /fasthtml/;
    }
    
    location /fasthtml/ {
        auth_request /oauth2/auth;
        error_page 401 = /oauth2/sign_in;
        auth_request_set $user $upstream_http_x_auth_request_user;
        proxy_set_header X-User $user;

        proxy_pass http://127.0.0.1:5001/;
        include /etc/nginx/fasthtml_proxy.conf;
    }
    
    # FastHTML API Routes
    location /fasthtml/api/ {
        auth_request /oauth2/auth;
        error_page 401 = /oauth2/sign_in;
        auth_request_set $user $upstream_http_x_auth_request_user;
        proxy_set_header X-User $user;

        proxy_pass http://127.0.0.1:5001/api/;
        include /etc/nginx/fasthtml_proxy.conf;
    }
    
    # FastHTML Static Files
    location /fasthtml/static/ {
        auth_request /oauth2/auth;
        error_page 401 = /oauth2/sign_in;
        auth_request_set $user $upstream_http_x_auth_request_user;
        proxy_set_header X-User $user;

        proxy_pass http://127.0.0.1:5001/static/;
        include /etc/nginx/fasthtml_proxy.conf;
    }
    
    # ========================================
    # ========================================
    # MILO CRM Application (port 5003)
    # ========================================

    location = /milo-crm {
        return 301 /milo-crm/;
    }

    location /milo-crm/ {
        auth_request /oauth2/auth;
        error_page 401 = /oauth2/sign_in;
        auth_request_set $user $upstream_http_x_auth_request_user;
        proxy_set_header X-User $user;

        proxy_pass http://127.0.0.1:5003/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Prefix /milo-crm;
        proxy_set_header Accept-Encoding "";

        # Rewrite redirects from app (e.g. /reports -> /milo-crm/reports)
        proxy_redirect / /milo-crm/;

        # Rewrite links in HTML content
        sub_filter_once off;
        sub_filter_types text/html;
        sub_filter 'href="/' 'href="/milo-crm/';
        sub_filter 'action="/' 'action="/milo-crm/';
        sub_filter 'hx-get="/' 'hx-get="/milo-crm/';
        sub_filter 'hx-post="/' 'hx-post="/milo-crm/';
        sub_filter 'hx-delete="/' 'hx-delete="/milo-crm/';
        sub_filter 'hx-put="/' 'hx-put="/milo-crm/';
        sub_filter 'hx-patch="/' 'hx-patch="/milo-crm/';
    }

    # ========================================
    # Oregon DEQ Site Browser (port 5010)
    # ========================================

    location = /oregon {
        return 301 /oregon/;
    }

    location /oregon/ {
        auth_request /oauth2/auth;
        error_page 401 = /oauth2/sign_in;
        auth_request_set $user $upstream_http_x_auth_request_user;
        proxy_set_header X-User $user;

        proxy_pass http://127.0.0.1:5010/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Prefix /oregon;
        proxy_set_header Accept-Encoding "";

        # WebSocket support (for live-reload in dev, harmless in prod)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_redirect / /oregon/;

        sub_filter_once off;
        sub_filter_types text/html;
        sub_filter 'href="/' 'href="/oregon/';
        sub_filter 'action="/' 'action="/oregon/';
        sub_filter 'hx-get="/' 'hx-get="/oregon/';
        sub_filter 'hx-post="/' 'hx-post="/oregon/';
        sub_filter 'hx-delete="/' 'hx-delete="/oregon/';
        sub_filter 'hx-put="/' 'hx-put="/oregon/';
        sub_filter 'hx-patch="/' 'hx-patch="/oregon/';
    }

    # ZipHandling Application (port 5002)
    # ========================================

    location = /ziphandling {
        return 301 /ziphandling/;
    }

    location /ziphandling/ {
        auth_request /oauth2/auth;
        error_page 401 = /oauth2/sign_in;
        auth_request_set $user $upstream_http_x_auth_request_user;
        proxy_set_header X-User $user;

        proxy_pass http://127.0.0.1:5002/;
        include /etc/nginx/fasthtml_proxy.conf;

        # Increase upload size for ZIP files
        client_max_body_size 2G;
    }

    # ZipHandling health check (no auth)
    location = /ziphandling/health {
        auth_request off;
        proxy_pass http://127.0.0.1:5002/health;
        include /etc/nginx/fasthtml_proxy.conf;
    }

    # Health Check (no authentication)
    # ========================================
    
    location = /health {
        auth_request off;
        proxy_pass http://127.0.0.1:5001/health;
        include /etc/nginx/fasthtml_proxy.conf;
    }

    # ========================================
    # Static Files for FastHTML (images) - no auth
    # ========================================
    
    location ~ ^/(logo\.svg|2025-Proven-Process\.png)$ {
        auth_request off;
        proxy_pass http://127.0.0.1:5001;
        include /etc/nginx/fasthtml_proxy.conf;
    }

    # ========================================
    # Process Endpoint (for qualification workflow)
    # ========================================
    
    location = /process {
        auth_request /oauth2/auth;
        error_page 401 = /oauth2/sign_in;
        auth_request_set $user $upstream_http_x_auth_request_user;
        proxy_set_header X-User $user;

        proxy_pass http://127.0.0.1:5001/process;
        include /etc/nginx/fasthtml_proxy.conf;
    }

    # ========================================
    # Process Async Endpoint (for HTMX polling during qualification)
    # ========================================
    
    location /process-async/ {
        auth_request /oauth2/auth;
        error_page 401 = /oauth2/sign_in;
        auth_request_set $user $upstream_http_x_auth_request_user;
        proxy_set_header X-User $user;

        proxy_pass http://127.0.0.1:5001/process-async/;
        include /etc/nginx/fasthtml_proxy.conf;
    }
    
    # ========================================
    # Counties Routes (public - no auth)
    # ========================================
    
    location = /counties {
        return 301 /counties/;
    }
    
    location /counties/ {
        auth_request /oauth2/auth;
        error_page 401 = /oauth2/sign_in;
        auth_request_set $user $upstream_http_x_auth_request_user;
        proxy_set_header X-User $user;

        proxy_pass http://127.0.0.1:5001/counties/;
        include /etc/nginx/fasthtml_proxy.conf;
    }
    
    location = /county-report-all {
        auth_request off;
        proxy_pass http://127.0.0.1:5001/county-report-all;
        include /etc/nginx/fasthtml_proxy.conf;
    }

    location = /county-report-all-pdf {
        auth_request off;
        proxy_pass http://127.0.0.1:5001/county-report-all-pdf;
        include /etc/nginx/fasthtml_proxy.conf;
    }

    # County report download endpoint (form handler)
    location = /county-report-download {
        auth_request off;
        proxy_pass http://127.0.0.1:5001/county-report-download;
        include /etc/nginx/fasthtml_proxy.conf;
    }

    # County report ZIP download
    location = /county-report-all-zip {
        auth_request off;
        proxy_pass http://127.0.0.1:5001/county-report-all-zip;
        include /etc/nginx/fasthtml_proxy.conf;
    }

    # County report redirect handler
    location = /county-report-redirect {
        auth_request off;
        proxy_pass http://127.0.0.1:5001/county-report-redirect;
        include /etc/nginx/fasthtml_proxy.conf;
    }
    
    # Customer Report PDF Download (public)
    location ~ ^/customer-report/([0-9]+)$ {
        auth_request off;
        proxy_pass http://127.0.0.1:5001/customer-report/$1;
        include /etc/nginx/fasthtml_proxy.conf;
    }

    # County report viewer (with dynamic parameter - public)
    location ~ ^/county-report/ {
        auth_request off;
        proxy_pass http://127.0.0.1:5001;
        include /etc/nginx/fasthtml_proxy.conf;
    }

    # ========================================
    # Root Path - Static files with Streamlit fallback
    # ========================================
    
    location / {
        auth_request /oauth2/auth;
        error_page 401 = /oauth2/sign_in;
        auth_request_set $user $upstream_http_x_auth_request_user;
        proxy_set_header X-User $user;

        root /var/www/html;
        index index.html index.htm;
        
        # Try to serve static file first, then directory, then fall back to Streamlit
        try_files $uri @streamlit;
    }
    
    # Named location for Streamlit proxy
    location @streamlit {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        
        # WebSocket support for Streamlit
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
        
        # Long timeout for Streamlit sessions
        proxy_read_timeout 86400;
    }

    listen [::]:443 ssl ipv6only=on; # managed by Certbot
    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/milo.restorical.com/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/milo.restorical.com/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot

}

server {
    if ($host = milo.restorical.com) {
        return 301 https://$host$request_uri;
    }

    listen 80;
    listen [::]:80;
    server_name milo.restorical.com;
    
    # Allow large file uploads (for ZipHandling)
    client_max_body_size 2G;
    return 404;
}
