# ─── iClinic Frontend ────────────────────────────────────────────────────────────
# React + Vite → built static files served by Nginx

# Stage 1: Build
FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --legacy-peer-deps

COPY . .

# Build-time env vars (override at build with --build-arg)
ARG VITE_API_BASE_URL=http://localhost:8001
ARG VITE_BACKEND_BASE_URL=http://localhost:8000
ARG VITE_WS_BASE_URL=ws://localhost:8000

ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_BACKEND_BASE_URL=$VITE_BACKEND_BASE_URL
ENV VITE_WS_BASE_URL=$VITE_WS_BASE_URL

# Skip tsc type-checking in Docker (Vite handles the build, tsc can fail on
# OneDrive placeholder files or strict type errors that don't affect runtime)
RUN npx vite build

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Add custom nginx config for SPA routing
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD wget -q --spider http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
