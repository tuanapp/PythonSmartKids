# Service Account Diagnostic Tools

Tools for verifying Google Play service account configuration and troubleshooting billing issues.

## 🔧 Available Tools

### 1. PowerShell Diagnostic (Windows)

**File:** `check-service-account.ps1`

**Quick Start:**
```powershell
# From environment variable
.\check-service-account.ps1 -FromEnv

# From file
.\check-service-account.ps1 -ServiceAccountPath "path\to\service-account.json"

# Interactive (will prompt for file path)
.\check-service-account.ps1
```

**What it does:**
- ✅ Checks Python installation
- ✅ Verifies required packages
- ✅ Loads service account JSON
- ✅ Displays service account email and project ID
- ✅ Runs comprehensive verification tests
- ✅ Provides actionable error messages

**Example Output:**
```
==================================================================
Google Play Service Account Checker
==================================================================

✅ Python found: Python 3.11.0
✅ Loaded from environment variable

📧 Service Account Email:
   smartboy-billing@project-name.iam.gserviceaccount.com

📦 Project ID:
   your-project-id

🔍 Running verification tests...
```

### 2. Python Verification Script

**File:** `../py/verify_service_account.py`

**Prerequisites:**
```bash
pip install google-auth google-auth-httplib2 google-api-python-client
```

**Usage:**
```bash
# Set environment variable first
export GOOGLE_APPLICATION_CREDENTIALS_JSON=$(cat service-account.json)

# Run verification
python ../py/verify_service_account.py
```

**What it checks:**
1. ✅ Environment variable is set
2. ✅ JSON structure is valid
3. ✅ All required fields present
4. ✅ Credentials can be created
5. ✅ API authentication works
6. ✅ Purchase verification permissions

**Example Output:**
```
======================================================================
Google Play Service Account Verification
======================================================================

✅ Service account JSON loaded

📋 Checking service account structure...
  ✅ type: service_account
  ✅ project_id: your-project
  ✅ client_email: smartboy-billing@project.iam.gserviceaccount.com
  ...

🔍 Testing API access...
✅ Service account can authenticate with Google Play API

🧪 Testing purchase verification permissions...
✅ Purchase verification permissions OK
```

## 🚨 Common Error Messages

### Error: "GOOGLE_APPLICATION_CREDENTIALS_JSON not set"

**Solution:**
```powershell
# PowerShell
$env:GOOGLE_APPLICATION_CREDENTIALS_JSON = Get-Content "service-account.json" -Raw

# Bash
export GOOGLE_APPLICATION_CREDENTIALS_JSON=$(cat service-account.json)
```

### Error: "401 Unauthorized"

**Meaning:** Service account lacks permissions in Google Play Console

**Solution:**
1. Go to Google Play Console → API access
2. Find your service account
3. Grant "View financial data" permission
4. Wait 5-10 minutes

**See:** [docs/GOOGLE_PLAY_401_QUICK_START.md](../../docs/GOOGLE_PLAY_401_QUICK_START.md)

### Error: "Missing required packages"

**Solution:**
```bash
pip install google-auth google-auth-httplib2 google-api-python-client
```

The PowerShell script will offer to install automatically.

## 📖 Documentation

- [Quick Start Guide](../../docs/GOOGLE_PLAY_401_QUICK_START.md) - 5-minute fix
- [Troubleshooting Guide](../../docs/GOOGLE_PLAY_401_TROUBLESHOOTING.md) - Comprehensive guide
- [Setup Checklist](../../docs/GOOGLE_PLAY_CONSOLE_CHECKLIST.md) - Complete setup
- [Billing Docs Index](../../docs/BILLING_DOCS_INDEX.md) - All billing documentation

## 🎯 Typical Workflow

### Initial Setup Verification
```powershell
# 1. Check service account configuration
.\check-service-account.ps1 -ServiceAccountPath "new-service-account.json"

# 2. If all checks pass, upload to Vercel
# Vercel Dashboard → Settings → Environment Variables
# Name: GOOGLE_APPLICATION_CREDENTIALS_JSON
# Value: <paste the JSON content>

# 3. Verify in Vercel environment
$env:GOOGLE_APPLICATION_CREDENTIALS_JSON = "PASTE_FROM_VERCEL"
.\check-service-account.ps1 -FromEnv
```

### Troubleshooting Production Issues
```powershell
# 1. Get service account JSON from Vercel
# Vercel Dashboard → Environment Variables → Copy value

# 2. Set locally for testing
$env:GOOGLE_APPLICATION_CREDENTIALS_JSON = "PASTE_VALUE"

# 3. Run diagnostic
.\check-service-account.ps1 -FromEnv

# 4. Check for specific errors
# - 401? Grant permissions in Play Console
# - Invalid JSON? Re-export from Google Cloud
# - Missing fields? Regenerate service account key
```

## 🔍 What the Tools Check

| Check | Description | Fix if Failed |
|-------|-------------|---------------|
| **Environment Variable** | `GOOGLE_APPLICATION_CREDENTIALS_JSON` is set | Set the variable with JSON content |
| **JSON Structure** | Valid JSON with required fields | Re-export service account key |
| **Service Account Email** | `client_email` field present | Regenerate service account |
| **Project ID** | `project_id` field present | Check Google Cloud project |
| **Private Key** | `private_key` field present | Regenerate key (don't share!) |
| **Authentication** | Can create credentials | Check JSON format |
| **API Access** | Can call Google Play API | Check internet connection |
| **Permissions** | Has purchase verification access | Grant permissions in Play Console |

## 💡 Pro Tips

1. **Keep Service Account Secure**
   - Never commit JSON to git
   - Use environment variables only
   - Rotate keys periodically

2. **Test Before Production**
   - Always test with a file first
   - Verify all checks pass
   - Only then upload to Vercel

3. **Monitor Regularly**
   - Run checks after any changes
   - Verify after rotating keys
   - Check when permissions change

4. **Debug Mode**
   - Use test accounts (UIDs: `kzJO9F*` or `zTCNk*`)
   - Enable debug panel in app (🔧 button)
   - Check API logs in debug panel

## 📞 Support

If verification fails and you can't resolve:
1. Check all error messages carefully
2. Review documentation links above
3. Contact WhatsApp support: +94769105555

## 🔗 Related Tools

- [Vercel CLI](https://vercel.com/docs/cli) - Manage environment variables
- [Google Cloud Console](https://console.cloud.google.com/) - Manage service accounts
- [Google Play Console](https://play.google.com/console) - Grant permissions

---

**Last Updated:** January 15, 2026  
**Location:** `Backend_Python/tools/`
