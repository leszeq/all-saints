FROM node:22-alpine AS dependencies

WORKDIR /workspace/apps/web
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci

FROM node:22-alpine AS builder

WORKDIR /workspace/apps/web
ARG NEXT_PUBLIC_API_URL=http://localhost
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_TELEMETRY_DISABLED=1 \
    NPM_CONFIG_UPDATE_NOTIFIER=false
COPY --from=dependencies /workspace/apps/web/node_modules ./node_modules
COPY apps/web ./
RUN npm run build -- --webpack

FROM node:22-alpine AS production

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000 \
    INTERNAL_API_URL=http://backend:8000

RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 --ingroup nodejs nextjs

WORKDIR /app/apps/web
COPY --from=builder --chown=nextjs:nodejs /workspace/apps/web/.next/standalone/apps/web ./
COPY --from=builder --chown=nextjs:nodejs /workspace/apps/web/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /workspace/apps/web/public ./public

USER nextjs
EXPOSE 3000

CMD ["node", "server.js"]
