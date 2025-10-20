FROM node:20-alpine AS build
WORKDIR /app
# Bring the whole apps/ tree so aliases like ../packages/* resolve
COPY tsconfig.base.json ./tsconfig.base.json
COPY apps ./apps
WORKDIR /app/apps/tenant

# Build-time configuration (overridable via build args)
ARG VITE_API_URL=https://api.gestiqcloud.com
ARG VITE_BASE_PATH=/
ARG VITE_TENANT_ORIGIN=https://gestiqcloud.com
ARG VITE_ADMIN_ORIGIN=https://admin.gestiqcloud.com
ENV VITE_API_URL=${VITE_API_URL}
ENV VITE_BASE_PATH=${VITE_BASE_PATH}
ENV VITE_TENANT_ORIGIN=${VITE_TENANT_ORIGIN}
ENV VITE_ADMIN_ORIGIN=${VITE_ADMIN_ORIGIN}

# Fix common native deps on Alpine (e.g., sharp/libvips via assets generator)
RUN apk add --no-cache libc6-compat && \
    npm i --silent || yarn install --frozen-lockfile || true
RUN ln -s /app/apps/tenant/node_modules /app/apps/node_modules || true

# Generate .env.production from build args
RUN /bin/sh -lc "printf 'VITE_API_URL=%s\nVITE_BASE_PATH=%s\nVITE_TENANT_ORIGIN=%s\nVITE_ADMIN_ORIGIN=%s\n' \"$VITE_API_URL\" \"$VITE_BASE_PATH\" \"$VITE_TENANT_ORIGIN\" \"$VITE_ADMIN_ORIGIN\" > .env.production"
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/apps/tenant/dist /usr/share/nginx/html
COPY apps/tenant/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8082
CMD ["nginx", "-g", "daemon off;"]

