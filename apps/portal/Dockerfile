FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm install

# Copy application code
COPY . .

# Build the Next.js app for production
# For development, we'll use the command override in docker-compose
RUN npm run build || true

EXPOSE 3000

# Default to dev mode (can be overridden in docker-compose)
CMD ["npm", "run", "dev"]

