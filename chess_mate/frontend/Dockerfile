# Build stage
FROM node:18-alpine as deps

# Set lower memory limit for Node
ENV NODE_OPTIONS="--max-old-space-size=2048"
ENV GENERATE_SOURCEMAP=false
ENV CI=false

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies with legacy peer deps and Babel plugins
RUN npm install --legacy-peer-deps \
    && npm install --save-dev \
    @babel/plugin-proposal-private-property-in-object@^7.21.11 \
    @babel/plugin-transform-private-property-in-object@^7.22.11 \
    @babel/plugin-transform-class-properties@^7.22.5 \
    @babel/plugin-transform-private-methods@^7.22.5 \
    @babel/plugin-transform-nullish-coalescing-operator@^7.22.5 \
    @babel/plugin-transform-numeric-separator@^7.22.5 \
    @babel/plugin-transform-optional-chaining@^7.22.5

# Build stage
FROM node:18-alpine as builder

WORKDIR /app

# Copy deps from previous stage
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Create babel config
RUN echo '{ "presets": ["react-app"], "plugins": ["@babel/plugin-proposal-private-property-in-object"] }' > .babelrc

# Create temporary .eslintrc
RUN echo '{ "extends": ["react-app"], "rules": { "no-unused-vars": "off", "react-hooks/exhaustive-deps": "off" } }' > .eslintrc

# Set environment variables for build
ENV NODE_OPTIONS="--max-old-space-size=2048"
ENV GENERATE_SOURCEMAP=false
ENV CI=false
ENV NODE_ENV=production

# Build the application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built assets from builder
COPY --from=builder /app/build /usr/share/nginx/html

# Configure nginx
RUN mkdir -p /usr/share/nginx/html && \
    chown -R nginx:nginx /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html

# Start nginx
CMD ["nginx", "-g", "daemon off;"] 