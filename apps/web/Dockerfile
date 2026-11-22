# Front image. Build from apps/web:
#   docker build --build-arg NEXT_PUBLIC_API_URL=http://localhost:8000 -t publifin-web .
# NEXT_PUBLIC_API_URL is the API address as seen by the browser. Next.js inlines it into the
# JavaScript bundle at build time: changing it means rebuilding the image.

# --- Dependencies: installed once, cached while package-lock.json does not change ---
FROM node:24.15.0-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# --- Build: output "standalone" keeps only the files the server needs ---
FROM node:24.15.0-slim AS build
WORKDIR /app
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules node_modules
COPY . .
RUN npm run build

# --- Runtime: minimal Node.js server, no node_modules from the build, non-root user ---
FROM node:24.15.0-slim
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static .next/static
USER node
EXPOSE 3000
CMD ["node", "server.js"]
