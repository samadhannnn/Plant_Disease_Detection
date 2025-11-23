# Memory Optimization Guide

## Changes Made for 512MB Memory Limit

### 1. TensorFlow Optimizations
- **Switched to `tensorflow-cpu`**: Lighter version without GPU support (saves ~100-200MB)
- **Disabled GPU**: Explicitly disabled GPU to prevent memory allocation
- **Memory growth limiting**: Configured TensorFlow to use memory growth instead of allocating all at once
- **Reduced logging**: Set `TF_CPP_MIN_LOG_LEVEL=2` to reduce memory overhead

### 2. Model Loading Optimizations
- **Lazy loading**: Model loads only when first prediction is made (not at startup)
- **Compile=False**: Load model without compilation first, then compile if needed
- **Batch size=1**: Use minimal batch size for predictions

### 3. Memory Cleanup
- **Garbage collection**: Explicit `gc.collect()` after each prediction
- **Variable cleanup**: Delete large variables immediately after use
- **Gunicorn worker recycling**: Workers restart after 50 requests to free memory

### 4. Gunicorn Configuration
- **Single worker**: Only 1 worker to reduce memory duplication
- **Worker recycling**: `--max-requests 50` to restart workers periodically
- **Reduced threads**: Only 1 thread per worker

## If Still Running Out of Memory

### Option 1: Upgrade Render Plan
Render's free tier has 512MB. You can upgrade to:
- **Starter Plan**: $7/month - 512MB RAM (same, but no spin-down)
- **Standard Plan**: $25/month - 2GB RAM (recommended for ML apps)

### Option 2: Use Railway.app
Railway offers:
- **Free tier**: 512MB RAM (similar to Render)
- **Hobby plan**: $5/month - 1GB RAM
- **Pro plan**: $20/month - 8GB RAM

### Option 3: Use Fly.io
Fly.io offers:
- **Free tier**: 256MB RAM (too small)
- **Shared CPU**: $1.94/month - 256MB RAM
- **Performance**: $5.70/month - 1GB RAM

### Option 4: Use Hugging Face Spaces
- **Free tier**: 16GB RAM (excellent for ML!)
- **CPU Spaces**: Free with 2 vCPU, 16GB RAM
- **GPU Spaces**: Free with limited GPU hours

### Option 5: Further Code Optimizations
If you need to stay on 512MB:
1. Convert model to TensorFlow Lite (saves ~50% memory)
2. Use model quantization (INT8 instead of FP32)
3. Implement model caching with disk swap
4. Use a smaller model architecture

## Recommended Solution

For a production ML app, I recommend:
1. **Hugging Face Spaces** (FREE, 16GB RAM) - Best for ML apps
2. **Railway Hobby** ($5/month, 1GB RAM) - Good balance
3. **Render Standard** ($25/month, 2GB RAM) - Most reliable
