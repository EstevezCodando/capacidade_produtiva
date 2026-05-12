# =============================================================================
# Stage 1 — builder
# Compila o React com Vite. node_modules NÃO vai para a imagem final.
# =============================================================================
FROM node:20-alpine AS builder

WORKDIR /app

# Instala dependências antes de copiar o código — aproveita o cache do Docker
COPY package.json package-lock.json ./
RUN npm ci --silent

# Código-fonte
COPY . .

# Build de produção — gera /app/dist com hashes nos nomes dos assets
RUN npm run build


# =============================================================================
# Stage 2 — runtime
# Nginx serve os arquivos estáticos e faz proxy de /api → backend:3050.
# Imagem final: ~25 MB, sem Node.js, sem npm, sem código-fonte.
# =============================================================================
FROM nginx:1.27-alpine AS runtime

# Remove a config default do nginx
RUN rm /etc/nginx/conf.d/default.conf

# Copia a config customizada (SPA routing + proxy /api)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Arquivos do build React
COPY --from=builder /app/dist /usr/share/nginx/html

# Nginx escuta em 80 internamente; o Compose mapeia para FRONTEND_PORT (5173)
EXPOSE 80

# Healthcheck: verifica se o nginx responde
HEALTHCHECK \
  --interval=15s \
  --timeout=5s \
  --start-period=10s \
  --retries=3 \
  CMD wget -qO- http://localhost/index.html > /dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
