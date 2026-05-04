FROM node:18-alpine AS builder

WORKDIR /app

ARG VITE_ADMIN_URL=http://localhost:8002
ENV VITE_ADMIN_URL=$VITE_ADMIN_URL

ARG VITE_DEV_MOCK_USER=false
ENV VITE_DEV_MOCK_USER=$VITE_DEV_MOCK_USER

ARG VITE_DEV_DEFAULT_EMAIL=
ENV VITE_DEV_DEFAULT_EMAIL=$VITE_DEV_DEFAULT_EMAIL

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
