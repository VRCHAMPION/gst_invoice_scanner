# 🚀 Deploy Frontend to Vercel - Quick Guide

## Option 1: One-Click Deploy (Easiest)

1. **Push to GitHub** (if not already)
   ```bash
   git add .
   git commit -m "Prepare for Vercel deployment"
   git push origin main
   ```

2. **Go to Vercel**
   - Visit: https://vercel.com/new
   - Click "Import Project"
   - Select your GitHub repo
   - Click "Import"

3. **Configure**
   ```
   Framework Preset: Other
   Root Directory: ./
   Build Command: (leave empty)
   Output Directory: frontend
   ```

4. **Deploy**
   - Click "Deploy"
   - Wait 30 seconds
   - Done! ✅

---

## Option 2: Vercel CLI (For Developers)

```bash
# Install Vercel CLI
npm install -g vercel

# Login
vercel login

# Deploy
vercel

# Deploy to production
vercel --prod
```

---

## ⚙️ Important: Update Backend CORS

After deploying, add your Vercel URL to backend CORS:

**File:** `backend/main.py`

```python
origins = [
    "http://localhost:3000",
    "http://localhost:8080",
    "https://your-project.vercel.app",  # Add this
    "https://*.vercel.app",  # Allow preview deployments
]
```

Then redeploy backend on Render.

---

## ✅ Test Your Deployment

1. Open `https://your-project.vercel.app`
2. Try to register/login
3. Upload an invoice
4. Check if API calls work (Network tab)

---

## 🐛 If API Calls Fail

1. Check `frontend/js/config.js` has correct backend URL
2. Check backend CORS allows your Vercel domain
3. Check browser console for errors

---

## 📝 Files Created

- ✅ `vercel.json` - Vercel configuration
- ✅ `frontend/js/config.js` - Updated with Vercel support
- ✅ `VERCEL_DEPLOYMENT.md` - Full documentation

---

## 🎉 That's It!

Your frontend is now on Vercel's global CDN with:
- ⚡ Instant page loads
- 🔒 Free HTTPS
- 🌍 Global edge network
- 🚀 Auto-deploy on git push

**Backend stays on Render** (already configured)

---

**Need help?** Check `VERCEL_DEPLOYMENT.md` for detailed guide.
