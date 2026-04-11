# Deploy Frontend to Vercel

## 📋 Prerequisites

1. **Vercel Account** - Sign up at [vercel.com](https://vercel.com)
2. **GitHub Repository** - Your code should be on GitHub
3. **Backend API** - Keep backend on Render (already configured)

---

## 🚀 Deployment Steps

### Method 1: Deploy via Vercel Dashboard (Easiest)

1. **Go to Vercel Dashboard**
   - Visit [vercel.com/new](https://vercel.com/new)
   - Click "Add New Project"

2. **Import Your Repository**
   - Connect your GitHub account
   - Select your `gst-invoice-scanner` repository
   - Click "Import"

3. **Configure Project**
   ```
   Framework Preset: Other
   Root Directory: ./
   Build Command: (leave empty)
   Output Directory: frontend
   Install Command: (leave empty)
   ```

4. **Add Environment Variables**
   - Click "Environment Variables"
   - Add these variables:
   
   ```
   Name: VITE_API_URL
   Value: https://your-render-backend.onrender.com
   
   Name: NODE_ENV
   Value: production
   ```

5. **Deploy**
   - Click "Deploy"
   - Wait 30-60 seconds
   - Your frontend will be live at `https://your-project.vercel.app`

---

### Method 2: Deploy via Vercel CLI

1. **Install Vercel CLI**
   ```bash
   npm install -g vercel
   ```

2. **Login to Vercel**
   ```bash
   vercel login
   ```

3. **Deploy from Project Root**
   ```bash
   vercel
   ```

4. **Follow Prompts**
   ```
   ? Set up and deploy "~/gst-invoice-scanner"? [Y/n] Y
   ? Which scope? Your Name
   ? Link to existing project? [y/N] N
   ? What's your project's name? gst-invoice-scanner
   ? In which directory is your code located? ./
   ```

5. **Set Environment Variables**
   ```bash
   vercel env add VITE_API_URL production
   # Enter: https://your-render-backend.onrender.com
   
   vercel env add NODE_ENV production
   # Enter: production
   ```

6. **Deploy to Production**
   ```bash
   vercel --prod
   ```

---

## 🔧 Configuration Files

### `vercel.json` (Already Created)
This file tells Vercel:
- Serve static files from `frontend/` directory
- Route all requests to frontend files
- Set proper cache headers for performance

### Update `frontend/js/config.js`
Make sure your API URL configuration supports production:

```javascript
function getApiUrl(endpoint) {
    // Check if running on Vercel
    if (window.location.hostname.includes('vercel.app')) {
        return 'https://your-render-backend.onrender.com' + endpoint;
    }
    
    // Local development
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        return 'http://localhost:8000' + endpoint;
    }
    
    // Netlify or other production
    return 'https://your-render-backend.onrender.com' + endpoint;
}
```

---

## 🌐 Custom Domain (Optional)

### Add Custom Domain to Vercel

1. **Go to Project Settings**
   - Open your project on Vercel
   - Click "Settings" → "Domains"

2. **Add Domain**
   - Enter your domain (e.g., `gstscanner.com`)
   - Click "Add"

3. **Configure DNS**
   - Add these records to your domain registrar:
   
   ```
   Type: CNAME
   Name: www
   Value: cname.vercel-dns.com
   
   Type: A
   Name: @
   Value: 76.76.21.21
   ```

4. **Wait for Verification**
   - DNS propagation takes 5-60 minutes
   - Vercel will auto-issue SSL certificate

---

## 📊 Deployment Architecture

```
┌─────────────────────────────────────────┐
│         USER'S BROWSER                  │
└─────────────┬───────────────────────────┘
              │
              ├─── Static Files (HTML/CSS/JS)
              │    ↓
              │    Vercel CDN (Frontend)
              │    https://your-project.vercel.app
              │
              └─── API Calls (/api/*)
                   ↓
                   Render (Backend)
                   https://your-backend.onrender.com
                   ↓
                   PostgreSQL Database
```

---

## ✅ Verification Checklist

After deployment, test these:

- [ ] Landing page loads (`/index.html`)
- [ ] Login page works (`/login.html`)
- [ ] Registration works (`/register.html`)
- [ ] Upload page loads (`/upload.html`)
- [ ] API calls reach backend (check Network tab)
- [ ] Authentication works (JWT tokens)
- [ ] File uploads work
- [ ] Results page displays data
- [ ] History page loads invoices
- [ ] Analytics page shows charts

---

## 🐛 Troubleshooting

### Issue: "API calls failing"
**Solution:** Check `frontend/js/config.js` has correct backend URL

### Issue: "CORS errors"
**Solution:** Add Vercel domain to backend CORS whitelist in `backend/main.py`:
```python
origins = [
    "http://localhost:3000",
    "http://localhost:8080",
    "https://your-project.vercel.app",  # Add this
    "https://*.vercel.app",  # Allow all Vercel preview deployments
]
```

### Issue: "404 on page refresh"
**Solution:** Already handled in `vercel.json` with routing rules

### Issue: "Environment variables not working"
**Solution:** 
1. Go to Vercel Dashboard → Project → Settings → Environment Variables
2. Add variables for all environments (Production, Preview, Development)
3. Redeploy: `vercel --prod`

---

## 🔄 Continuous Deployment

Vercel automatically deploys when you push to GitHub:

1. **Push to `main` branch** → Production deployment
2. **Push to other branches** → Preview deployment
3. **Pull requests** → Preview deployment with unique URL

### Disable Auto-Deploy (Optional)
```bash
vercel --prod --no-auto-deploy
```

---

## 💰 Pricing

### Vercel Free Tier Includes:
- ✅ Unlimited deployments
- ✅ 100GB bandwidth/month
- ✅ Automatic HTTPS
- ✅ Global CDN
- ✅ Preview deployments
- ✅ Custom domains

**Perfect for your frontend!**

---

## 📈 Performance Optimization

### Already Configured in `vercel.json`:
- Static asset caching (1 year for JS/CSS)
- HTML caching (1 hour with revalidation)
- Automatic compression (gzip/brotli)
- Edge network delivery

### Additional Optimizations:
1. **Minify JS/CSS** (optional)
   ```bash
   npm install -g terser csso-cli
   terser frontend/js/*.js -o frontend/js/bundle.min.js
   csso frontend/css/style.css -o frontend/css/style.min.css
   ```

2. **Image Optimization**
   - Use WebP format for images
   - Compress images before upload

---

## 🔐 Security

### Environment Variables
Never commit these to Git:
- API keys
- Database URLs
- JWT secrets

Always use Vercel's environment variables dashboard.

### HTTPS
Vercel automatically provides:
- Free SSL certificates
- Automatic renewal
- HTTP → HTTPS redirect

---

## 📝 Quick Commands

```bash
# Deploy to preview
vercel

# Deploy to production
vercel --prod

# Check deployment status
vercel ls

# View logs
vercel logs

# Remove deployment
vercel rm your-deployment-url

# Open project in browser
vercel open
```

---

## 🎉 Success!

Your frontend is now deployed on Vercel with:
- ⚡ Lightning-fast global CDN
- 🔒 Automatic HTTPS
- 🚀 Instant deployments
- 🌍 Custom domain support
- 📊 Analytics dashboard

**Live URL:** `https://your-project.vercel.app`

---

## 📞 Support

- **Vercel Docs:** [vercel.com/docs](https://vercel.com/docs)
- **Vercel Discord:** [vercel.com/discord](https://vercel.com/discord)
- **Status Page:** [vercel-status.com](https://vercel-status.com)

---

**Deployment Date:** 2026-04-11  
**Status:** ✅ Ready to Deploy
