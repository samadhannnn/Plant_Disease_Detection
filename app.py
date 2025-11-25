from flask import Flask, render_template,request,redirect,send_from_directory,url_for,Response
import numpy as np
import json
import uuid
import os
import tensorflow as tf
import cv2
import threading
import time

app = Flask(__name__)
model = tf.keras.models.load_model("models/plant_disease_recog_model_pwp.keras")

# OpenCV Camera Setup
camera = None
camera_lock = threading.Lock()
current_frame = None
camera_active = False
camera_initialized = False

def find_builtin_camera():
    """Find the built-in laptop camera (Mac/Windows) by checking available cameras"""
    import platform
    system = platform.system()
    
    available_cameras = []
    
    print("Scanning for available cameras...")
    
    # Check first 10 camera indices
    for i in range(10):
        try:
            # Use appropriate backend based on OS
            if system == 'Darwin':  # macOS
                test_camera = cv2.VideoCapture(i, cv2.CAP_AVFOUNDATION)
            elif system == 'Windows':
                test_camera = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            else:
                test_camera = cv2.VideoCapture(i)
            
            if test_camera.isOpened():
                # Try to get a frame to verify it works
                ret, frame = test_camera.read()
                if ret and frame is not None:
                    # Get camera properties
                    width = test_camera.get(cv2.CAP_PROP_FRAME_WIDTH)
                    height = test_camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
                    backend = test_camera.getBackendName()
                    
                    available_cameras.append({
                        'index': i,
                        'backend': backend,
                        'width': width,
                        'height': height,
                        'works': True
                    })
                    print(f"✓ Found camera at index {i}: {backend}, resolution: {int(width)}x{int(height)}")
                else:
                    print(f"✗ Camera at index {i} opened but failed to read frame")
                test_camera.release()
            else:
                print(f"✗ Could not open camera at index {i}")
        except Exception as e:
            print(f"✗ Error testing camera {i}: {e}")
            # Try with default backend if OS-specific backend fails
            try:
                test_camera = cv2.VideoCapture(i)
                if test_camera.isOpened():
                    ret, frame = test_camera.read()
                    if ret and frame is not None:
                        width = test_camera.get(cv2.CAP_PROP_FRAME_WIDTH)
                        height = test_camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
                        available_cameras.append({
                            'index': i,
                            'backend': 'default',
                            'width': width,
                            'height': height,
                            'works': True
                        })
                        print(f"✓ Found camera at index {i} (default backend), resolution: {int(width)}x{int(height)}")
                    test_camera.release()
            except:
                pass
    
    print(f"Total available cameras: {len(available_cameras)}")
    
    if not available_cameras:
        print("❌ No cameras found! This could be due to:")
        print("   - Camera not connected")
        print("   - Camera permissions denied")
        print("   - Camera being used by another application")
        print("   - Driver issues")
        return None
    
    # Strategy to find built-in laptop camera:
    # 1. If only one camera, use it (likely built-in)
    # 2. If multiple cameras:
    #    - On Mac: Built-in is often at index 1 when external devices are at 0
    #    - On Windows: Built-in is usually at index 0, external at higher indices
    #    - Prefer camera with higher resolution (built-in usually has better quality)
    #    - Prefer camera at lower index (built-in is usually first)
    
    if len(available_cameras) == 1:
        print(f"✓ Single camera detected at index {available_cameras[0]['index']} (using as built-in)")
        return available_cameras[0]['index']
    
    # Multiple cameras - find the best one for built-in
    if system == 'Darwin':  # macOS
        # On Mac, if external device is connected, built-in is often at index 1
        index_1_camera = next((cam for cam in available_cameras if cam['index'] == 1), None)
        if index_1_camera:
            print(f"✓ macOS: Multiple cameras detected. Using index 1 (Mac built-in camera)")
            return 1
        # If no index 1, prefer highest resolution (built-in usually better)
        builtin_camera = max(available_cameras, key=lambda x: x.get('width', 0) * x.get('height', 0))
        print(f"✓ macOS: Using index {builtin_camera['index']} (highest resolution: {builtin_camera.get('width')}x{builtin_camera.get('height')})")
        return builtin_camera['index']
    
    elif system == 'Windows':
        # On Windows, built-in is usually at index 0
        index_0_camera = next((cam for cam in available_cameras if cam['index'] == 0), None)
        if index_0_camera:
            print(f"✓ Windows: Multiple cameras detected. Using index 0 (Windows built-in camera)")
            return 0
        # Fallback to highest resolution
        builtin_camera = max(available_cameras, key=lambda x: x.get('width', 0) * x.get('height', 0))
        print(f"✓ Windows: Using index {builtin_camera['index']} (highest resolution)")
        return builtin_camera['index']
    
    else:
        # Linux or other - use index 0 or highest resolution
        index_0_camera = next((cam for cam in available_cameras if cam['index'] == 0), None)
        if index_0_camera:
            print(f"✓ Linux: Using index 0 (default camera)")
            return 0
        builtin_camera = max(available_cameras, key=lambda x: x.get('width', 0) * x.get('height', 0))
        print(f"✓ Linux: Using index {builtin_camera['index']} (highest resolution)")
        return builtin_camera['index']

def init_camera():
    global camera, camera_initialized
    try:
        with camera_lock:
            if camera is not None and camera.isOpened():
                return True
            
            # Release any existing camera first
            if camera is not None:
                try:
                    camera.release()
                except:
                    pass
                camera = None
            
            # Find the best camera index (Mac built-in)
            camera_index = find_builtin_camera()
            if camera_index is None:
                print("❌ No cameras found during scan, trying fallback methods...")
                # Try common fallback indices
                fallback_indices = [0, 1, 2]
                for idx in fallback_indices:
                    print(f"Trying fallback camera index {idx}...")
                    try:
                        test_cam = cv2.VideoCapture(idx)
                        if test_cam.isOpened():
                            ret, frame = test_cam.read()
                            if ret and frame is not None:
                                camera_index = idx
                                print(f"✓ Fallback successful: Using camera index {idx}")
                                test_cam.release()
                                break
                            test_cam.release()
                    except:
                        pass
                
                if camera_index is None:
                    print("❌ All fallback methods failed")
                    return False
            else:
                print(f"✓ Using camera index {camera_index} from scan")
            
            # Use OS-appropriate backend for better compatibility
            import platform
            system = platform.system()
            
            # Try multiple backends for maximum compatibility
            backends_to_try = []
            if system == 'Darwin':  # macOS
                backends_to_try = [cv2.CAP_AVFOUNDATION, cv2.CAP_ANY]
            elif system == 'Windows':
                backends_to_try = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
            else:
                backends_to_try = [cv2.CAP_V4L2, cv2.CAP_ANY]
            
            camera = None
            for backend in backends_to_try:
                try:
                    print(f"Trying backend {backend} with camera index {camera_index}...")
                    camera = cv2.VideoCapture(camera_index, backend)
                    
                    if camera.isOpened():
                        # Test if we can actually read a frame
                        ret, test_frame = camera.read()
                        if ret and test_frame is not None:
                            print(f"✓ Camera opened successfully with backend {backend}")
                            break
                        else:
                            print(f"✗ Camera opened but failed to read frame with backend {backend}")
                            camera.release()
                            camera = None
                    else:
                        print(f"✗ Failed to open camera with backend {backend}")
                        if camera:
                            camera.release()
                            camera = None
                except Exception as e:
                    print(f"✗ Error with backend {backend}: {e}")
                    if camera:
                        camera.release()
                        camera = None
            
            # Final fallback - try without any backend specification
            if camera is None or not camera.isOpened():
                print("Trying final fallback without backend specification...")
                try:
                    camera = cv2.VideoCapture(camera_index)
                    if camera.isOpened():
                        ret, test_frame = camera.read()
                        if ret and test_frame is not None:
                            print("✓ Final fallback successful")
                        else:
                            print("✗ Final fallback failed - no frame read")
                            camera.release()
                            camera = None
                    else:
                        print("✗ Final fallback failed - camera not opened")
                        camera = None
                except Exception as e:
                    print(f"✗ Final fallback error: {e}")
                    camera = None
            
            if camera is not None and camera.isOpened():
                # Set camera properties
                try:
                    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                    camera.set(cv2.CAP_PROP_FPS, 30)
                    
                    # Verify settings
                    actual_width = camera.get(cv2.CAP_PROP_FRAME_WIDTH)
                    actual_height = camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
                    actual_fps = camera.get(cv2.CAP_PROP_FPS)
                    
                    print(f"Camera properties set: {int(actual_width)}x{int(actual_height)} @ {actual_fps} FPS")
                except Exception as e:
                    print(f"Warning: Could not set camera properties: {e}")
                
                # Try to get camera backend info
                try:
                    backend = camera.getBackendName()
                    print(f"Camera backend: {backend}")
                except:
                    print("Could not get backend name")
                
                camera_initialized = True
                print("✓ Camera initialization completed successfully")
                return True
            else:
                camera = None
                camera_initialized = False
                print("❌ Failed to initialize camera with all methods")
                return False
                
    except Exception as e:
        print(f"❌ Critical error initializing camera: {e}")
        import traceback
        traceback.print_exc()
        with camera_lock:
            camera = None
            camera_initialized = False
        return False

def release_camera():
    global camera, camera_active, camera_initialized
    with camera_lock:
        camera_active = False
        if camera is not None:
            try:
                if camera.isOpened():
                    camera.release()
            except Exception as e:
                print(f"Error releasing camera: {e}")
            finally:
                camera = None
                camera_initialized = False
        time.sleep(0.1)  # Small delay to ensure cleanup

def generate_frames():
    global camera, current_frame, camera_active, camera_initialized
    
    print("Starting video feed generation...")
    
    # Initialize camera if needed
    with camera_lock:
        if not camera_initialized or camera is None or not camera.isOpened():
            print("Camera not initialized, initializing now...")
            if not init_camera():
                print("Failed to initialize camera in generate_frames")
                return
        camera_active = True
        local_camera = camera  # Get reference to camera
        print(f"Camera initialized, active: {camera_active}")
    
    frame_count = 0
    try:
        while True:
            # Check if camera should be active (with lock, but quick check)
            with camera_lock:
                if not camera_active:
                    print("Camera marked as inactive, stopping feed")
                    break
                if camera is None or camera != local_camera:
                    print("Camera reference changed, stopping feed")
                    break
                if not camera.isOpened():
                    print("Camera not opened, stopping feed")
                    break
            
            # Read frame outside lock to avoid blocking
            try:
                success, frame = local_camera.read()
                if not success or frame is None:
                    # Check again if camera is still valid
                    with camera_lock:
                        if not camera_active or camera != local_camera:
                            break
                    # Retry reading
                    time.sleep(0.01)
                    continue
            except Exception as e:
                print(f"Error reading frame: {e}")
                # Don't break immediately, try to continue
                time.sleep(0.1)
                continue
            
            # Process frame
            try:
                # Flip frame horizontally for mirror effect
                frame = cv2.flip(frame, 1)
                # Encode frame as JPEG
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if not ret:
                    continue
                
                # Update current_frame with lock
                with camera_lock:
                    if camera_active:  # Only update if still active
                        current_frame = frame.copy()
                
                frame_bytes = buffer.tobytes()
                frame_count += 1
                
                # Yield frame in multipart format
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            except Exception as e:
                print(f"Error processing frame: {e}")
                continue
    except GeneratorExit:
        print("Video feed client disconnected")
    except Exception as e:
        print(f"Error in generate_frames: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"Video feed ended. Total frames: {frame_count}")
        # Don't release camera here - let it be managed by stop_camera route
        # Just mark as inactive
        with camera_lock:
            camera_active = False
label = ['Apple___Apple_scab',
 'Apple___Black_rot',
 'Apple___Cedar_apple_rust',
 'Apple___healthy',
 'Background_without_leaves',
 'Blueberry___healthy',
 'Cherry___Powdery_mildew',
 'Cherry___healthy',
 'Corn___Cercospora_leaf_spot Gray_leaf_spot',
 'Corn___Common_rust',
 'Corn___Northern_Leaf_Blight',
 'Corn___healthy',
 'Grape___Black_rot',
 'Grape___Esca_(Black_Measles)',
 'Grape___Leaf_blight_(Isariopsis_Leaf_Spot)',
 'Grape___healthy',
 'Orange___Haunglongbing_(Citrus_greening)',
 'Peach___Bacterial_spot',
 'Peach___healthy',
 'Pepper,_bell___Bacterial_spot',
 'Pepper,_bell___healthy',
 'Potato___Early_blight',
 'Potato___Late_blight',
 'Potato___healthy',
 'Raspberry___healthy',
 'Soybean___healthy',
 'Squash___Powdery_mildew',
 'Strawberry___Leaf_scorch',
 'Strawberry___healthy',
 'Tomato___Bacterial_spot',
 'Tomato___Early_blight',
 'Tomato___Late_blight',
 'Tomato___Leaf_Mold',
 'Tomato___Septoria_leaf_spot',
 'Tomato___Spider_mites Two-spotted_spider_mite',
 'Tomato___Target_Spot',
 'Tomato___Tomato_Yellow_Leaf_Curl_Virus',
 'Tomato___Tomato_mosaic_virus',
 'Tomato___healthy']

with open("plant_disease.json",'r') as file:
    plant_disease = json.load(file)

# print(plant_disease[4])

@app.route('/uploadimages/<path:filename>')
def uploaded_images(filename):
    return send_from_directory('./uploadimages', filename)

@app.route('/video_feed')
def video_feed():
    try:
        return Response(generate_frames(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')
    except Exception as e:
        print(f"Error in video_feed route: {e}")
        return Response(b'', status=500)

@app.route('/capture_frame', methods=['POST'])
def capture_frame():
    global current_frame, camera
    try:
        frame_to_save = None
        with camera_lock:
            if current_frame is not None:
                frame_to_save = current_frame.copy()
            elif camera is not None and camera.isOpened():
                # Try to capture a fresh frame
                success, frame = camera.read()
                if success and frame is not None:
                    frame_to_save = cv2.flip(frame, 1)
        
        if frame_to_save is None:
            return render_template('index.html', error='No frame available. Please start camera first.')
        
        # Save captured frame
        temp_name = f"uploadimages/temp_{uuid.uuid4().hex}_capture.jpg"
        cv2.imwrite(temp_name, frame_to_save)
        
        # Predict
        prediction = model_predict(f'./{temp_name}')
        
        return render_template('index.html',
                             result=True,
                             imagepath=f'/{temp_name}',
                             prediction=prediction)
    except Exception as e:
        print(f"Error capturing frame: {e}")
        return render_template('index.html', error=f"Capture failed: {str(e)}")

@app.route('/list_cameras', methods=['GET'])
def list_cameras():
    """List all available cameras"""
    import platform
    system = platform.system()
    cameras = []
    
    for i in range(10):
        try:
            # Use OS-appropriate backend
            if system == 'Darwin':  # macOS
                test_camera = cv2.VideoCapture(i, cv2.CAP_AVFOUNDATION)
            elif system == 'Windows':
                test_camera = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            else:
                test_camera = cv2.VideoCapture(i)
            
            if test_camera.isOpened():
                ret, frame = test_camera.read()
                if ret and frame is not None:
                    width = test_camera.get(cv2.CAP_PROP_FRAME_WIDTH)
                    height = test_camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
                    cameras.append({
                        'index': i,
                        'width': int(width),
                        'height': int(height)
                    })
                test_camera.release()
        except:
            # Try default backend
            try:
                test_camera = cv2.VideoCapture(i)
                if test_camera.isOpened():
                    ret, frame = test_camera.read()
                    if ret and frame is not None:
                        width = test_camera.get(cv2.CAP_PROP_FRAME_WIDTH)
                        height = test_camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
                        cameras.append({
                            'index': i,
                            'width': int(width),
                            'height': int(height)
                        })
                    test_camera.release()
            except:
                pass
    return {'cameras': cameras, 'system': system}

@app.route('/start_camera', methods=['POST'])
def start_camera():
    global camera, camera_initialized, camera_active
    try:
        # Get preferred camera index from request (optional)
        camera_index = request.json.get('camera_index') if request.is_json else None
        
        with camera_lock:
            if camera is not None and camera.isOpened() and camera_initialized:
                camera_active = True
                return {'status': 'success', 'message': 'Camera already running'}
        
        # If specific camera index requested, use it
        if camera_index is not None:
            print(f"Using requested camera index: {camera_index}")
            with camera_lock:
                if camera is not None:
                    try:
                        camera.release()
                    except:
                        pass
                    camera = None
            
            try:
                import platform
                system = platform.system()
                
                if system == 'Darwin':  # macOS
                    camera = cv2.VideoCapture(camera_index, cv2.CAP_AVFOUNDATION)
                elif system == 'Windows':
                    camera = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
                else:
                    camera = cv2.VideoCapture(camera_index)
                
                if not camera.isOpened():
                    camera = cv2.VideoCapture(camera_index)
                
                if camera.isOpened():
                    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                    camera.set(cv2.CAP_PROP_FPS, 30)
                    camera_initialized = True
                    camera_active = True
                    return {'status': 'success', 'message': f'Camera {camera_index} started'}
            except Exception as e:
                print(f"Error starting camera {camera_index}: {e}")
        
        # Otherwise use auto-detection
        if init_camera():
            with camera_lock:
                camera_active = True
            print("Camera started successfully")
            return {'status': 'success', 'message': 'Camera started'}
        else:
            return {'status': 'error', 'message': 'Failed to start camera. Please check if camera is available.'}, 500
    except Exception as e:
        print(f"Error in start_camera: {e}")
        import traceback
        traceback.print_exc()
        return {'status': 'error', 'message': str(e)}, 500

@app.route('/stop_camera', methods=['POST'])
def stop_camera():
    global camera_active
    try:
        # Set flag first to stop frame generation (with lock)
        with camera_lock:
            camera_active = False
        
        time.sleep(0.2)  # Wait for frame generation to stop
        release_camera()
        return {'status': 'success', 'message': 'Camera stopped'}
    except Exception as e:
        print(f"Error in stop_camera: {e}")
        # Ensure camera is released even on error
        try:
            with camera_lock:
                camera_active = False
            release_camera()
        except:
            pass
        return {'status': 'error', 'message': str(e)}, 500

@app.route('/',methods = ['GET'])
def home():
    return render_template('index.html')

def extract_features(image):
    image = tf.keras.utils.load_img(image,target_size=(160,160))
    feature = tf.keras.utils.img_to_array(image)
    feature = np.array([feature])
    return feature

def model_predict(image):
    img = extract_features(image)
    prediction = model.predict(img)
    # print(prediction)
    prediction_label = plant_disease[prediction.argmax()]
    return prediction_label

@app.route('/upload/',methods = ['POST','GET'])
def uploadimage():
    if request.method == "POST":
        image = request.files['img']
        temp_name = f"uploadimages/temp_{uuid.uuid4().hex}"
        image.save(f'{temp_name}_{image.filename}')
        print(f'{temp_name}_{image.filename}')
        prediction = model_predict(f'./{temp_name}_{image.filename}')
        return render_template('index.html',result=True,imagepath = f'/{temp_name}_{image.filename}', prediction = prediction )
    
    else:
        return redirect('/')
        
    
# Cleanup on app shutdown
import atexit

@atexit.register
def cleanup_on_exit():
    release_camera()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    print(f"🌿 Starting PlantAI Disease Recognition System on http://127.0.0.1:{port}")
    print(f"📸 Webcam capture feature enabled!")
    try:
        app.run(debug=debug, host="127.0.0.1", port=port)
    finally:
        # Ensure camera is released on exit
        release_camera()
