# Docker Setup for Flask App

This document explains how to run the Flask application using Docker.

## Prerequisites

- Docker installed on your system
- Docker Compose installed on your system

## Quick Start

1. **Copy environment variables:**

   ```bash
   cp env.example .env
   ```

2. **Edit the .env file** with your actual configuration values:

   ```bash
   # Edit .env file with your API keys and database credentials
   nano .env
   ```

3. **Build and run with Docker Compose:**

   ```bash
   docker-compose up --build
   ```

4. **Access the application:**
   - Open your browser and go to `http://localhost:8000`

## Manual Docker Commands

If you prefer to use Docker directly:

1. **Build the image:**

   ```bash
   docker build -t flask-app .
   ```

2. **Run the container:**
   ```bash
   docker run -p 8000:8000 --env-file .env -v $(pwd)/uploads:/app/uploads flask-app
   ```

## Environment Variables

The application requires several environment variables to be set in the `.env` file:

- `SECRET_KEY`: Flask secret key for sessions
- `DATABASE_URL`: PostgreSQL connection string
- `OPENAI_API_KEY`: OpenAI API key for AI features
- `SUPABASE_URL` & `SUPABASE_KEY`: Supabase configuration
- `PINECONE_API_KEY` & `PINECONE_ENVIRONMENT`: Pinecone vector database
- `GOOGLE_AI_API_KEY`: Google AI API key
- `TAVILY_API_KEY`: Tavily search API key

## Docker Features

- **Multi-stage build** for optimized image size
- **Health checks** to monitor application status
- **Volume mounting** for persistent uploads
- **Environment variable support** via .env file
- **Production-ready** with debug mode disabled
- **Uvicorn WSGI server** for better performance

## Troubleshooting

### Port already in use

If port 8000 is already in use, change the port in `docker-compose.yml`:

```yaml
ports:
  - "8001:8000" # Use port 8001 on host
```

### Environment variables not loading

Ensure your `.env` file is in the same directory as `docker-compose.yml` and contains valid key-value pairs.

### Permission issues with uploads

The uploads directory is mounted as a volume. Ensure proper permissions:

```bash
chmod 755 uploads/
```

## Production Deployment

For production deployment:

1. Use a proper reverse proxy (nginx, traefik)
2. Set up SSL/TLS certificates
3. Use environment-specific .env files
4. Consider using Docker Swarm or Kubernetes for orchestration
5. Set up proper logging and monitoring
