# Deployment Guide - Plant Disease Recognition System

## Deploying to Render (Free Tier)

### Step 1: Create a Render Account
1. Go to [https://render.com](https://render.com)
2. Sign up for a free account (you can use GitHub to sign in)

### Step 2: Create a New Web Service
1. Click on "New +" button in the dashboard
2. Select "Web Service"
3. Connect your GitHub account if not already connected
4. Select the repository: `samadhannnn/Plant-Disease-Recognition-System`

### Step 3: Configure the Service
1. **Name**: `plant-disease-recognition` (or any name you prefer)
2. **Region**: Choose the closest region to you
3. **Branch**: `main`
4. **Root Directory**: Leave empty (or use `.` if required)
5. **Environment**: `Python 3`
6. **Build Command**: `pip install -r requirements.txt`
7. **Start Command**: `gunicorn app:app --workers 1 --threads 1 --timeout 120`
8. **Plan**: Select "Free" plan

### Step 4: Environment Variables (Optional)
You can add these if needed:
- `FLASK_ENV`: `production`
- `PYTHON_VERSION`: `3.11.0`

### Step 5: Deploy
1. Click "Create Web Service"
2. Render will automatically:
   - Clone your repository
   - Install dependencies
   - Download the model from Google Drive (first time only)
   - Start the application

### Step 6: Access Your Application
- Once deployment is complete, you'll get a URL like: `https://plant-disease-recognition.onrender.com`
- The first deployment may take 5-10 minutes
- The app will spin down after 15 minutes of inactivity (free tier limitation)
- First request after spin-down may take 30-60 seconds to wake up

## Important Notes

1. **Model Download**: The model will be automatically downloaded from Google Drive on first startup. This may take a few minutes.

2. **Free Tier Limitations**:
   - Service spins down after 15 minutes of inactivity
   - 750 hours/month free (enough for always-on if you're the only user)
   - First request after spin-down has a cold start delay

3. **File Storage**: Uploaded images are stored in the `uploadimages` directory. On Render's free tier, these files are ephemeral and will be deleted when the service restarts. For production, consider using cloud storage (AWS S3, Cloudinary, etc.).

## Alternative: Railway.app (Another Free Option)

Railway also offers a free tier and is very easy to use:

1. Go to [https://railway.app](https://railway.app)
2. Sign up with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your repository
5. Railway will auto-detect it's a Python app
6. Add start command: `gunicorn app:app --workers 1 --threads 1 --timeout 120`
7. Deploy!

## Troubleshooting

- If deployment fails, check the build logs in Render dashboard
- Ensure all dependencies in `requirements.txt` are correct
- The model download may timeout - if so, the app will retry on next request
- Check that the Google Drive link is accessible
