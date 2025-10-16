FROM node:20-alpine AS build
WORKDIR /app
# Bring the whole apps/ tree so aliases like ../packages/* resolve
COPY tsconfig.base.json ./tsconfig.base.json
COPY apps ./apps
WORKDIR /app/apps/admin
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
