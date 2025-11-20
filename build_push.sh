#!/bin/bash

IMAGE_NAME="okkarkp/dmw-validator-ai"
VERSION_TAG="v1.3"

echo "🔧 Checking buildx builder..."
if ! docker buildx ls | grep -q multiarch; then
    echo "📌 Creating buildx builder 'multiarch'..."
    docker buildx create --use --name multiarch
    docker buildx inspect --bootstrap
else
    echo "✅ Using existing buildx builder."
    docker buildx use multiarch
fi

echo "🚀 Building and pushing multi-arch image..."
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t ${IMAGE_NAME}:latest \
  -t ${IMAGE_NAME}:${VERSION_TAG} \
  --push .

echo "🎉 Build & push completed!"
echo "🟢 Images pushed:"
echo "   - ${IMAGE_NAME}:latest"
echo "   - ${IMAGE_NAME}:${VERSION_TAG}"
