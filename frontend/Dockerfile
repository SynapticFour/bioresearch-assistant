# node:20-alpine hat offizielle ARM64 Unterstützung ✓
FROM node:25-alpine AS builder
WORKDIR /app
ARG VITE_API_URL=http://localhost:8000
ARG VITE_APP_VERSION=1.3.0
ARG VITE_DEPLOYMENT=local
ARG VITE_INSTITUTION=Meine Institution
ENV VITE_API_URL=$VITE_API_URL \
    VITE_APP_VERSION=$VITE_APP_VERSION \
    VITE_DEPLOYMENT=$VITE_DEPLOYMENT \
    VITE_INSTITUTION=$VITE_INSTITUTION
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# nginx:alpine hat offizielle ARM64 Unterstützung ✓
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
