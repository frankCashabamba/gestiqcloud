FROM node:20-alpine AS build
WORKDIR /app
# Bring the whole apps/ tree so aliases like ../packages/* resolve
COPY tsconfig.base.json ./tsconfig.base.json
COPY apps ./apps
WORKDIR /app/apps/admin

# Accept VITE_* at build time to override .env.production when building dev images
ARG VITE_API_URL
ARG VITE_BASE_PATH
ARG VITE_TENANT_ORIGIN
ARG VITE_ADMIN_ORIGIN
ENV VITE_API_URL=${VITE_API_URL}
ENV VITE_BASE_PATH=${VITE_BASE_PATH}
ENV VITE_TENANT_ORIGIN=${VITE_TENANT_ORIGIN}
ENV VITE_ADMIN_ORIGIN=${VITE_ADMIN_ORIGIN}

RUN apk add --no-cache libc6-compat && \
    npm i --silent || yarn install --frozen-lockfile || true
RUN ln -s /app/apps/admin/node_modules /app/apps/node_modules || true
# Usa el .env.production commiteado en el repo (no sobrescribir). 
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/apps/admin/dist /usr/share/nginx/html
COPY apps/admin/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8081
CMD ["nginx", "-g", "daemon off;"]
