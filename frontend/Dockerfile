# Build stage
FROM node:22-alpine AS builder

ARG VITE_API_URL

ENV VITE_API_URL=$VITE_API_URL

WORKDIR /app

# Install all dependencies (including dev)
COPY frontend/package*.json ./
RUN npm ci

# Copy source and build
COPY frontend/ ./
RUN npm run build

# Production stage
FROM node:22-alpine

WORKDIR /app

# O servidor empacotado mantém apenas dependências Node de runtime.
COPY frontend/package*.json ./
RUN npm ci --omit=dev --ignore-scripts && npm cache clean --force

# Copy build artifacts from builder
COPY --from=builder /app/dist ./dist

ENV NODE_ENV=production
ENV PORT=5173
EXPOSE 5173
USER node

# Start the express server using the built bundle
CMD ["npm", "start"]
