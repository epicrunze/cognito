# Multi-stage Dockerfile for Cognito SvelteKit Frontend

# Stage 1: Build the SvelteKit application
FROM node:20-slim AS build

WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Use .env.docker for build (Vite bakes env vars at build time)
RUN if [ -f .env.docker ]; then cp .env.docker .env; fi

# Sync SvelteKit and build the static site
RUN npm run prepare && npm run build

# Stage 2: Serve with nginx
FROM nginx:alpine AS production

# Remove default nginx config
RUN rm -f /etc/nginx/conf.d/default.conf

# Copy custom nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Copy built static files from build stage
COPY --from=build /app/build /usr/share/nginx/html

# Expose port 3000 (matches nginx upstream in reverse proxy)
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/health || exit 1

# Run nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
