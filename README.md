# Door Detection Web Application - Setup Guide

## Overview
This is a web-based door detection system with TWO main features:
1. **Live Detection** - Real-time camera-based door monitoring
2. **Video Upload** - Process pre-recorded videos to detect door status

---

## Quick Start

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Run the Application
```bash
python app.py
```

### Step 3: Open in Browser
```
http://localhost:5000
```

---

## Features

### 🔴 LIVE DETECTION (Left Panel)

**What it does:**
- Monitors door in real-time using your webcam
- Shows live video feed
- Detects when door opens/closes
- Logs all status changes

**How to use:**
1. Click **"Start Live Detection"** button
2. Click **"Set Door Frame"** and enter coordinates (e.g., `100,100,300,400`)
   - Format: `x,y,width,height`
   - x,y = top-left corner
   - width,height = size of door frame
3. **Close your door completely**
4. Click **"Calibrate Closed"** button
5. Done! System now detects OPEN/CLOSED automatically

**Controls:**
- **Start Live Detection** - Starts camera feed
- **Stop Detection** - Stops camera and shows history
- **Set Door Frame** - Define area to monitor
- **Calibrate Closed** - Save what "closed" looks like
- **+ / -** - Adjust sensitivity (how much change = door opened)

**Tips:**
- Make door frame tight around the door only
- Don't include walls or walking areas
- Calibrate when door is fully closed
- Increase sensitivity (+) for slow-opening doors
- Decrease sensitivity (-) if getting false detections

---

### 📁 VIDEO UPLOAD DETECTION (Right Panel)

**What it does:**
- Analyzes pre-recorded video files
- Detects door open/close throughout the video
- Shows frame-by-frame results with timestamps
- Exports detection data

**How to use:**
1. Click **upload area** or drag-and-drop a video file
2. Wait for video to upload
3. First frame appears - Click **"Set Door Frame"** and enter coordinates
4. Click **"Process Video"** to analyze entire video
5. View results in the table below

**Supported formats:**
- MP4, AVI, MOV, MKV
- Any format OpenCV supports

**Output:**
- Table showing:
  - Frame number
  - Timestamp (MM:SS)
  - Status (OPEN/CLOSED)
  - Change percentage

---

## How ROI (Door Frame) Works

### What is ROI?
ROI = Region of Interest = the rectangle around your door

### Why is it important?
- System ONLY monitors this area
- Everything outside ROI is ignored
- Prevents false detections from people/furniture

### How to determine ROI coordinates?

**Method 1: Estimate from image**
```
If your door is roughly:
- 100 pixels from left edge (x = 100)
- 100 pixels from top edge (y = 100)  
- 300 pixels wide (width = 300)
- 400 pixels tall (height = 400)

Enter: 100,100,300,400
```

**Method 2: Trial and error**
1. Start with estimate
2. See if rectangle covers door
3. Adjust and try again

**Example coordinates:**
```
Small door center:     200,150,200,300
Large door left side:  50,100,400,500
Double doors:          100,100,600,500
```

---

## Technical Details

### Detection Algorithm
1. System captures "closed door" reference image
2. Each frame, compares current door to reference
3. Calculates pixel difference percentage
4. If > threshold (default 5%) → OPEN
5. If < threshold → CLOSED

### Sensitivity Setting
- Default: 5% change = door opened
- Range: 1% (very sensitive) to 15% (less sensitive)
- Adjust based on:
  - Lighting conditions
  - Door type (sliding vs swinging)
  - Camera quality

---

## Troubleshooting

### Live Detection Issues

**Problem: Camera not working**
- Solution: Check camera permissions
- Try different camera index (modify code: `cv2.VideoCapture(0)` → `cv2.VideoCapture(1)`)

**Problem: False positives (detecting OPEN when closed)**
- Solution: Decrease sensitivity (click -)
- Check ROI doesn't include areas with movement
- Recalibrate with door fully closed

**Problem: Not detecting when door opens**
- Solution: Increase sensitivity (click +)
- Make sure ROI covers the moving part of door
- Ensure good lighting

**Problem: "Not Calibrated" message**
- Solution: Make sure you:
  1. Set door frame first
  2. Close door completely
  3. Then calibrate

### Video Upload Issues

**Problem: Upload fails**
- Solution: Check video file size (< 100MB recommended)
- Try converting to MP4 format
- Check file isn't corrupted

**Problem: Processing takes too long**
- Solution: Long videos take time (1-2 min per 1000 frames)
- For faster testing, use shorter clips
- Consider trimming video first

**Problem: Inaccurate results**
- Solution: First frame should show door CLOSED
- Set ROI carefully around door
- If first frame shows open door, trim video to start when closed

---

## File Structure

```
door-detection-app/
├── app.py                  # Flask backend
├── requirements.txt        # Dependencies
├── templates/
│   └── index.html         # Web interface
└── uploads/               # Temporary video storage (auto-created)
```

---

## Advanced Configuration

### Change Default Settings

Edit `app.py`:

```python
# Line 15: Default sensitivity
self.threshold_percentage = 5.0  # Change to 3.0 for more sensitive

# Line 403: Camera resolution
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)   # Change to 1280 for higher quality
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)  # Change to 720
```

### Add Authentication

To restrict access, add Flask-Login or basic auth.

### Database Integration

Currently stores history in memory. To persist:
- Add SQLite/PostgreSQL
- Store detections with timestamps
- Query historical data

---

## API Endpoints

If you want to integrate with other systems:

```
POST /start_live          - Start live detection
POST /stop_live           - Stop live detection
POST /set_roi             - Set door frame (JSON: {x, y, width, height})
POST /calibrate           - Calibrate closed position
POST /adjust_sensitivity  - Adjust threshold (JSON: {action: 'increase'/'decrease'})
GET  /video_feed          - Live video stream
POST /upload_video        - Upload video file
POST /set_video_roi       - Set video door frame
POST /process_video       - Process uploaded video
```

---

## Performance

### System Requirements
- Python 3.7+
- Webcam (for live detection)
- 2GB RAM minimum
- Any modern browser

### Expected Performance
- Live detection: 15-30 FPS
- Video processing: ~50-100 frames/second
- Latency: < 100ms detection time

---

## Future Enhancements

Possible additions:
- Mobile app version
- Email/SMS alerts when door opens
- Multiple door monitoring
- Cloud storage for videos
- Machine learning for better accuracy
- Night vision support
- Sound alerts

---

## Support

For issues:
1. Check troubleshooting section
2. Verify all dependencies installed
3. Check console for error messages
4. Ensure camera permissions granted

---

## License

This is a custom door detection system. Use freely for personal/commercial projects.

---

## Summary

**Live Detection:**
Start → Set Frame → Calibrate → Detect ✅

**Video Upload:**
Upload → Set Frame → Process → View Results ✅

Both use the exact same detection logic - just different input sources!
