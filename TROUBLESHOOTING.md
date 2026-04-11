# Troubleshooting Guide

## Invoice Processing Failures

### Symptom
All uploaded invoices fail with error: "Failed to parse invoice data."

### Root Cause
The Gemini API is not working, which could be due to:

1. **Missing or Invalid API Key** (Most Likely)
   - The `GEMINI_API_KEY` environment variable is not set in Render
   - Or the API key is invalid/expired

2. **API Quota Exceeded**
   - You've hit the free tier rate limits
   - Need to wait or upgrade quota

3. **Model Availability Issues**
   - Gemini models not available in your region
   - API endpoint issues

### Solution Steps

#### 1. Check Render Environment Variables
1. Go to your Render dashboard
2. Navigate to your backend service
3. Click on "Environment" tab
4. Verify `GEMINI_API_KEY` is set with a valid API key
5. If missing or wrong, add/update it:
   - Key: `GEMINI_API_KEY`
   - Value: Your actual Gemini API key from Google AI Studio

#### 2. Get a Valid Gemini API Key
1. Visit: https://aistudio.google.com/app/apikey
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key and add it to Render environment variables

#### 3. Check API Quota
1. Visit: https://aistudio.google.com/app/apikey
2. Check your API usage and quota limits
3. If exceeded, wait for reset or request quota increase

#### 4. Test Locally First
Before deploying, test locally:
```bash
cd backend
# Set your API key
export GEMINI_API_KEY="your-key-here"

# Run the app
python run.py

# Upload a test invoice through the UI
```

#### 5. Check Render Logs
After setting the environment variable and redeploying:
1. Go to Render dashboard → Your service → Logs
2. Upload a test invoice
3. Look for these log entries:
   - `gemini_success` - API call worked ✅
   - `gemini_model_not_found` - Model name issue
   - `gemini_api_error` - API authentication or other error
   - `gemini_all_models_failed` - All models failed (likely auth issue)

### Expected Behavior After Fix
- Logs should show: `"event": "gemini_success", "model": "gemini-1.5-flash-latest"`
- Invoices should process successfully
- Invoice data should be extracted and displayed

### Still Not Working?
Check the detailed error logs in Render. The improved logging will show:
- Which Gemini model is being tried
- Exact error messages from the API
- Whether it's an auth issue, rate limit, or other problem
