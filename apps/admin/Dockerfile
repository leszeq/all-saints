FROM node:22-alpine AS dependencies

WORKDIR /workspace/apps/admin
COPY apps/admin/package.json apps/admin/package-lock.json ./
RUN npm ci

FROM node:22-alpine AS builder

WORKDIR /workspace/apps/admin
ARG NEXT_PUBLIC_API_URL=http://localhost:8080
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_TELEMETRY_DISABLED=1 \
    NPM_CONFIG_UPDATE_NOTIFIER=false
COPY --from=dependencies /workspace/apps/admin/node_modules ./node_modules
COPY apps/admin ./
RUN npm run build -- --webpack

FROM node:22-alpine AS production

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000

RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 --ingroup nodejs nextjs

WORKDIR /app/apps/admin
COPY --from=builder --chown=nextjs:nodejs /workspace/apps/admin/.next/standalone/apps/admin ./
COPY --from=builder --chown=nextjs:nodejs /workspace/apps/admin/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /workspace/apps/admin/public ./public

USER nextjs
EXPOSE 3000

CMD ["node", "server.js"]
