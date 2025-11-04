#!/bin/bash

# MAS-Eval Google Cloud Run Deployment Script
# Usage: ./deploy.sh [PROJECT_ID] [REGION]

set -e

# Configuration
PROJECT_ID=${1:-"your-gcp-project-id"}
REGION=${2:-"europe-west1"}
SERVICE_NAME="mas-eval"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "🚀 Deploying MAS-Eval to Google Cloud Run"
echo "================================================"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo "================================================"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI is not installed"
    exit 1
fi

# Set project
echo "📋 Setting GCP project..."
gcloud config set project ${PROJECT_ID}

# Build container image
echo "🔨 Building container image..."
gcloud builds submit --tag ${IMAGE_NAME}

# Deploy to Cloud Run
echo "☁️  Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --max-instances 10 \
    --set-env-vars OPENAI_API_KEY=${OPENAI_API_KEY} \
    --set-env-vars OPENAI_MODEL=gpt-4o-mini \
    --set-env-vars LOG_LEVEL=INFO

echo "✅ Deployment completed!"
echo ""
echo "Service URL:"
gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)'
