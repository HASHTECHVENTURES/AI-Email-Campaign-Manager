# 🚀 Vercel Deployment Guide

## Quick Deploy to Vercel

### 1. Install Vercel CLI
```bash
npm i -g vercel
```

### 2. Deploy
```bash
# In your project directory
vercel

# Follow the prompts:
# - Set up and deploy? Y
# - Which scope? (select your account)
# - Link to existing project? N
# - Project name: ai-email-campaign-manager
# - Directory: ./
# - Override settings? N
```

### 3. Set Environment Variables
In Vercel dashboard, go to Settings → Environment Variables:

```
EMAIL = your-gmail@gmail.com
PASSWORD = your-gmail-app-password
GEMINI_API_KEY = your-gemini-api-key
```

### 4. Redeploy
```bash
vercel --prod
```

## Environment Variables Explained

- **EMAIL**: Your Gmail address for sending emails
- **PASSWORD**: Gmail App Password (not your regular password)
- **GEMINI_API_KEY**: Your Google Gemini API key

## Gmail App Password Setup

1. Enable 2-Factor Authentication on Gmail
2. Go to Google Account Settings
3. Security → 2-Step Verification → App passwords
4. Generate password for "Mail"
5. Use this password in Vercel environment variables

## Features After Deployment

✅ **Automatic Email Monitoring** - Checks for replies every 30 seconds
✅ **AI-Powered Responses** - Automatic replies using Gemini AI
✅ **Real-time Dashboard** - Live conversation tracking
✅ **Contact Management** - Add/remove contacts via CSV upload
✅ **Campaign Management** - Send bulk emails with tracking

## Production URLs

After deployment, your app will be available at:
- `https://your-project-name.vercel.app`

## Monitoring

The system automatically:
- Monitors Gmail inbox for replies
- Generates AI responses
- Updates dashboard in real-time
- Tracks conversation statistics

No manual intervention needed!