# SickDroneProject Debug & Testing Instructions

## 🚀 How to Run the Tests

### Step 1: Make sure the Flask server is running
1. Open a terminal/command prompt
2. Navigate to your project directory:
   ```
   cd c:\Users\andre\Desktop\SickDroneProject
   ```
3. Start the Flask server:
   ```
   python -m sdronep.app
   ```
4. You should see output like:
   ```
   🚀 Starting Drone Control System
   📹 Camera controls available on interface
   📱 GPS UDP receiver listening on port 11123 for phone GPS
   🌐 Access the interface at: http://localhost:3000
   * Running on http://127.0.0.1:3000
   ```

### Step 2: Run the API Testing Script
In a **new terminal window** (keep the Flask server running):
```bash
cd c:\Users\andre\Desktop\SickDroneProject
python test_api_debug.py
```

This script will:
- Test all API endpoints
- Check CORS configuration  
- Verify data formats
- Show detailed error messages
- Provide recommendations

### Step 3: Open the Debug Test Page
1. Open your web browser
2. Navigate to: `file:///c:/Users/andre/Desktop/SickDroneProject/debug_test.html`
3. Click "Test Server Connection" first
4. Then test other API endpoints
5. Try "Start Live Updates" to test real-time communication

### Step 4: Check the Original Website
1. Open: http://localhost:3000
2. Open browser Developer Tools (F12)
3. Go to Console tab
4. Look for JavaScript errors (red text)
5. Go to Network tab
6. Refresh page and watch for failed requests

## 🔍 What to Look For

### ✅ Good Signs:
- API test script shows "All endpoints working"
- Debug page shows "Connection successful"
- No JavaScript errors in browser console
- Network requests show status 200
- Live updates work in debug page

### ❌ Problem Signs:
- Connection errors in API test
- JavaScript errors in console
- Failed network requests (red in Network tab)
- CORS errors mentioning "blocked by CORS policy"
- Empty responses or timeout errors

## 🐛 Common Issues & Fixes

### Issue 1: "Connection refused" or "Server not running"
**Fix:** Make sure Flask server is running (Step 1)

### Issue 2: CORS errors
**Fix:** The flask-cors package should be installed and working now

### Issue 3: JavaScript not updating
**Possible causes:**
1. Browser caching - try Ctrl+F5 (hard refresh)
2. JavaScript errors - check console
3. Wrong URL in JavaScript - should be localhost:3000

### Issue 4: Logs not showing
**Check:**
1. Are logs being generated? (API test will show)
2. Is drone tracking active? (logs only appear when tracking)
3. JavaScript console errors?

### Issue 5: Drone location showing 0,0
**Fix:** 
1. Click "Start Drone Tracking" on the website
2. Make sure drone is connected via ESP32 WiFi

## 📋 Information to Provide

After running the tests, please share:

1. **API Test Results**: Copy the entire output from `test_api_debug.py`
2. **Browser Console Logs**: 
   - Open F12 → Console tab on http://localhost:3000
   - Take screenshot or copy error messages
3. **Network Tab Results**:
   - Open F12 → Network tab on http://localhost:3000  
   - Refresh page
   - Take screenshot showing request status
4. **Debug Page Results**: What happens when you test the debug page?

## 🔧 Quick Fixes to Try

### If API test script works but website doesn't:
```bash
# Clear browser cache
- Press Ctrl+Shift+Delete
- Select "Cached images and files"
- Clear data
- Try again
```

### If JavaScript errors mention CORS:
The flask-cors package is now installed. Restart the Flask server:
```bash
# Stop the server (Ctrl+C)
# Then restart:
python -m sdronep.app
```

### If nothing works:
Try the debug test page first - it's simpler and will help isolate the issue.

## 📞 Next Steps

Run all the tests above and share the results. The debug information will help identify exactly what's going wrong and provide a targeted fix.

The most common issues are:
1. **Server not running** - Fixed by Step 1
2. **CORS blocked requests** - Should be fixed now with flask-cors
3. **JavaScript caching** - Fixed with hard refresh
4. **Missing DOM elements** - The debug page will test this

Let me know what you find! 🚀
