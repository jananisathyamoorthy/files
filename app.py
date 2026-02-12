from flask import Flask, render_template, Response, request, jsonify
import cv2
import numpy as np
from datetime import datetime
import base64
import threading
import os
import time

app = Flask(__name__)

# Global variables for live detection
live_detector = None
live_camera = None
live_active = False
live_lock = threading.Lock()

# Global variables for video detection
video_detector = None
current_video_path = None
video_filename = None

class SimpleDoorDetector:
    def __init__(self):
        """Simple, reliable door detector with fixed ROI"""
        self.door_roi = None
        self.reference_closed = None
        self.door_status = "Unknown"
        self.history = []
        self.threshold_percentage = 5.0
        
    def set_door_frame(self, roi):
        """Set the fixed frame around the door"""
        self.door_roi = roi
        
    def calibrate_closed(self, frame):
        """Capture what door looks like when CLOSED"""
        if self.door_roi is None:
            return False
            
        x, y, w, h = self.door_roi
        door_area = frame[y:y+h, x:x+w]
        self.reference_closed = cv2.cvtColor(door_area, cv2.COLOR_BGR2GRAY)
        self.reference_closed = cv2.GaussianBlur(self.reference_closed, (15, 15), 0)
        return True
    
    def detect_door_status(self, frame):
        """Detect if door is open or closed by comparing to reference"""
        if self.door_roi is None or self.reference_closed is None:
            return "Not Calibrated", None, 0
        
        x, y, w, h = self.door_roi
        current_door = frame[y:y+h, x:x+w]
        current_gray = cv2.cvtColor(current_door, cv2.COLOR_BGR2GRAY)
        current_gray = cv2.GaussianBlur(current_gray, (15, 15), 0)
        
        diff = cv2.absdiff(self.reference_closed, current_gray)
        _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
        changed_pixels = np.sum(thresh > 0)
        total_pixels = thresh.size
        change_percentage = (changed_pixels / total_pixels) * 100
        
        if change_percentage > self.threshold_percentage:
            status = "OPEN"
        else:
            status = "CLOSED"
        
        vis = current_door.copy()
        diff_colored = cv2.applyColorMap(diff, cv2.COLORMAP_JET)
        
        color = (0, 0, 255) if status == "OPEN" else (0, 255, 0)
        cv2.putText(vis, f"Change: {change_percentage:.1f}%", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(vis, status, (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
        
        return status, (vis, diff_colored, thresh), change_percentage
    
    def log_status(self, status):
        """Log status changes"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if len(self.history) == 0 or self.history[-1]['status'] != status:
            self.history.append({'timestamp': timestamp, 'status': status})


def generate_live_frames():
    """Generator for live video streaming"""
    global live_detector, live_camera, live_active
    
    while live_active:
        if live_camera is None or live_detector is None:
            break
            
        ret, frame = live_camera.read()
        if not ret:
            break
        
        display_frame = frame.copy()
        
        # Draw door frame
        if live_detector.door_roi:
            x, y, w, h = live_detector.door_roi
            cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 255, 255), 2)
            cv2.putText(display_frame, "DOOR FRAME", (x, y-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        # Detect door status
        status, processed, change_pct = live_detector.detect_door_status(frame)
        
        # Log status
        if status in ["OPEN", "CLOSED"]:
            live_detector.log_status(status)
        
        # Display status
        status_color = (0, 255, 0) if status == "CLOSED" else (0, 0, 255)
        cv2.rectangle(display_frame, (5, 5), (300, 60), (0, 0, 0), -1)
        cv2.putText(display_frame, f"Door: {status}", (10, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, status_color, 3)
        
        cv2.putText(display_frame, f"Sensitivity: {live_detector.threshold_percentage:.1f}%", (10, 80),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Encode frame
        ret, buffer = cv2.imencode('.jpg', display_frame)
        frame_bytes = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


def generate_video_playback():
    """Generator for video playback with door detection overlay"""
    global video_detector, current_video_path
    
    if not current_video_path or not os.path.exists(current_video_path):
        return
    
    cap = cv2.VideoCapture(current_video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        display_frame = frame.copy()
        
        # Draw door frame
        if video_detector and video_detector.door_roi:
            x, y, w, h = video_detector.door_roi
            cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 255, 255), 3)
        
        # Detect door status
        if video_detector:
            status, _, change_pct = video_detector.detect_door_status(frame)
            
            # Calculate timestamp
            timestamp = frame_count / fps if fps > 0 else frame_count
            time_str = f"{int(timestamp // 60):02d}:{int(timestamp % 60):02d}"
            
            # Display status overlay
            status_color = (0, 255, 0) if status == "CLOSED" else (0, 0, 255)
            
            # Create semi-transparent overlay at top
            overlay = display_frame.copy()
            height, width = display_frame.shape[:2]
            cv2.rectangle(overlay, (0, 0), (width, 100), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.7, display_frame, 0.3, 0, display_frame)
            
            # Status text - larger and more prominent
            cv2.putText(display_frame, f"Door: {status}", (20, 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, status_color, 4)
            
            # Frame info
            cv2.putText(display_frame, f"Frame: {frame_count} | Time: {time_str} | Change: {change_pct:.1f}%",
                       (20, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        frame_count += 1
        
        # Encode frame
        ret, buffer = cv2.imencode('.jpg', display_frame)
        frame_bytes = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    
    cap.release()


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')


@app.route('/start_live', methods=['POST'])
def start_live():
    """Start live detection"""
    global live_detector, live_camera, live_active
    
    with live_lock:
        if live_active:
            return jsonify({'success': False, 'message': 'Already running'})
        
        live_camera = cv2.VideoCapture(0)
        if not live_camera.isOpened():
            return jsonify({'success': False, 'message': 'Camera not available'})
        
        live_camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        live_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        live_detector = SimpleDoorDetector()
        live_active = True
        
        return jsonify({'success': True, 'message': 'Live detection started'})


@app.route('/stop_live', methods=['POST'])
def stop_live():
    """Stop live detection"""
    global live_detector, live_camera, live_active
    
    with live_lock:
        live_active = False
        if live_camera:
            live_camera.release()
            live_camera = None
        
        history = live_detector.history if live_detector else []
        live_detector = None
        
        return jsonify({'success': True, 'history': history})


@app.route('/video_feed')
def video_feed():
    """Video streaming route"""
    return Response(generate_live_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/set_roi', methods=['POST'])
def set_roi():
    """Set ROI for door detection"""
    global live_detector
    
    data = request.json
    roi = (data['x'], data['y'], data['width'], data['height'])
    
    if live_detector:
        live_detector.set_door_frame(roi)
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': 'Detector not initialized'})


@app.route('/calibrate', methods=['POST'])
def calibrate():
    """Calibrate closed position"""
    global live_detector, live_camera
    
    if live_detector and live_camera:
        ret, frame = live_camera.read()
        if ret:
            success = live_detector.calibrate_closed(frame)
            return jsonify({'success': success})
    
    return jsonify({'success': False, 'message': 'Not ready'})


@app.route('/get_frame', methods=['GET'])
def get_frame():
    """Get current frame for ROI selection"""
    global live_camera
    
    if live_camera:
        ret, frame = live_camera.read()
        if ret:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_b64 = base64.b64encode(buffer).decode('utf-8')
            return jsonify({'success': True, 'frame': frame_b64})
    
    return jsonify({'success': False})


@app.route('/adjust_sensitivity', methods=['POST'])
def adjust_sensitivity():
    """Adjust detection sensitivity"""
    global live_detector
    
    data = request.json
    action = data.get('action')
    
    if live_detector:
        if action == 'increase':
            live_detector.threshold_percentage = max(1.0, live_detector.threshold_percentage - 0.5)
        elif action == 'decrease':
            live_detector.threshold_percentage = min(15.0, live_detector.threshold_percentage + 0.5)
        
        return jsonify({'success': True, 'value': live_detector.threshold_percentage})
    
    return jsonify({'success': False})


@app.route('/upload_video', methods=['POST'])
def upload_video():
    """Upload video for processing"""
    global video_detector, current_video_path, video_filename
    
    if 'video' not in request.files:
        return jsonify({'success': False, 'message': 'No video file'})
    
    video_file = request.files['video']
    video_filename = video_file.filename
    
    # Save uploaded file
    os.makedirs('uploads', exist_ok=True)
    current_video_path = os.path.join('uploads', video_filename)
    video_file.save(current_video_path)
    
    # Initialize detector
    video_detector = SimpleDoorDetector()
    
    cap = cv2.VideoCapture(current_video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    # Get first frame for ROI selection
    ret, first_frame = cap.read()
    if not ret:
        return jsonify({'success': False, 'message': 'Could not read video'})
    
    # Encode first frame
    ret, buffer = cv2.imencode('.jpg', first_frame)
    frame_b64 = base64.b64encode(buffer).decode('utf-8')
    
    cap.release()
    
    return jsonify({
        'success': True,
        'first_frame': frame_b64,
        'total_frames': total_frames,
        'fps': fps,
        'filename': video_filename
    })


@app.route('/set_video_roi', methods=['POST'])
def set_video_roi():
    """Set ROI for video processing"""
    global video_detector
    
    data = request.json
    roi = (data['x'], data['y'], data['width'], data['height'])
    
    if video_detector:
        video_detector.set_door_frame(roi)
        return jsonify({'success': True})
    
    return jsonify({'success': False})


@app.route('/calibrate_video', methods=['POST'])
def calibrate_video():
    """Calibrate video with first frame"""
    global video_detector, current_video_path
    
    if not video_detector or not current_video_path:
        return jsonify({'success': False, 'message': 'Not ready'})
    
    cap = cv2.VideoCapture(current_video_path)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        return jsonify({'success': False, 'message': 'Could not read video'})
    
    # Calibrate with first frame
    success = video_detector.calibrate_closed(frame)
    
    return jsonify({'success': success})


@app.route('/video_playback_feed')
def video_playback_feed():
    """Stream processed video with door status overlay"""
    return Response(generate_video_playback(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    app.run(debug=True, threaded=True, port=5000)