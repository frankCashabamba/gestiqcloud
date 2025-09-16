FROM node:20-alpine AS build
WORKDIR /app
# Bring the whole apps/ tree so aliases like ../packages/* resolve
COPY apps ./apps
WORKDIR /app/apps/tenant
# Fix common native deps on Alpine (e.g., sharp/libvips via assets generator)
RUN apk add --no-cache libc6-compat && \
    npm i --silent || yarn install --frozen-lockfile || true
RUN ln -s /app/apps/tenant/node_modules /app/apps/node_modules || true
RUN echo 'VITE_API_URL=/api' > .env.production
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/apps/tenant/dist /usr/share/nginx/html
COPY apps/tenant/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8082
CMD ["nginx", "-g", "daemon off;"]
