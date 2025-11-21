FROM node:20-alpine

# Create non-root user
RUN adduser -D -u 1000 sandbox

# Set working directory
WORKDIR /workspace

# Set user
USER sandbox

# Default command
CMD ["node"]
