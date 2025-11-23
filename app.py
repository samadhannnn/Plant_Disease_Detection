import os
import uuid
import json
import numpy as np
import tensorflow as tf
import gdown
from flask import Flask, render_template, request, redirect, send_from_directory
import gc

# ---------------- MEMORY OPTIMIZATION ----------------
# Configure TensorFlow to use minimal memory
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Reduce TensorFlow logging
# Disable GPU to save memory (use CPU only)
tf.config.set_visible_devices([], 'GPU')
# Set TensorFlow to use minimal memory allocation
try:
    # Limit memory growth for GPU (if any)
    gpus = tf.config.experimental.list_physical_devices('GPU')
    if gpus:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
except:
    pass
# Set inter/intra op parallelism to reduce memory
os.environ['TF_NUM_INTEROP_THREADS'] = '1'
os.environ['TF_NUM_INTRAOP_THREADS'] = '1'

# ---------------- CONFIG ----------------

MODEL_DIR = "models"
MODEL_NAME = "plant_disease_recog_model_pwp.keras"
MODEL_PATH = os.path.join(MODEL_DIR, MODEL_NAME)

# Google Drive model file
MODEL_FILE_ID = "1SdiOAGFlq-I7dgGjLQdi4onfx1JBLwlT"
MODEL_URL = f"https://drive.google.com/uc?id={MODEL_FILE_ID}"

UPLOAD_DIR = "uploadimages"
IMG_SIZE = (160, 160)

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

# ---------------- MODEL DOWNLOAD + LOAD ----------------

def download_model_if_needed():
    if not os.path.exists(MODEL_PATH):
        print("⚠️ Model not found locally. Downloading...")
        gdown.download(MODEL_URL, MODEL_PATH, quiet=False)
        print("✅ Model downloaded.")


def load_keras_model():
    download_model_if_needed()
    print("📦 Loading model...")
    # Load model with compile=False to save memory
    model = tf.keras.models.load_model(MODEL_PATH, compile=False)
    # Compile only if needed (some models require compilation)
    try:
        model.compile()
    except:
        pass
    print("✅ Model loaded.")
    return model


app = Flask(__name__)

# Lazy load model to reduce initial memory footprint
_model = None

def get_model():
    global _model
    if _model is None:
        _model = load_keras_model()
    return _model

# ---------------- DISEASE CLASS JSON ----------------

with open("plant_disease.json", "r") as file:
    plant_disease = json.load(file)


# ---------------- ROUTES ----------------

@app.route('/uploadimages/<path:filename>')
def uploaded_images(filename):
    return send_from_directory(UPLOAD_DIR, filename)


@app.route('/')
def home():
    return render_template('index.html')


# ---------------- PREDICTION ----------------

def extract_features(image_path):
    img = tf.keras.utils.load_img(image_path, target_size=IMG_SIZE)
    arr = tf.keras.utils.img_to_array(img)
    return np.expand_dims(arr, 0)


def model_predict(image_path):
    model = get_model()  # Get model (lazy loaded)
    img = extract_features(image_path)
    # Use predict with smaller batch and verbose=0 to save memory
    pred = model.predict(img, batch_size=1, verbose=0)
    idx = int(np.argmax(pred))
    # Clear memory
    del img, pred
    gc.collect()
    return plant_disease[idx]


@app.route('/upload/', methods=['POST'])
def uploadimage():
    image = request.files.get('img')
    if not image or image.filename == "":
        return redirect('/')

    save_path = f"{UPLOAD_DIR}/temp_{uuid.uuid4().hex}_{image.filename}"
    image.save(save_path)

    try:
        prediction = model_predict(save_path)
    except Exception as e:
        print(f"Prediction error: {e}")
        # Clean up on error
        if os.path.exists(save_path):
            os.remove(save_path)
        return render_template('index.html', error="Prediction failed. Please try again.")
    finally:
        # Clean up uploaded file after prediction to save space
        # Keep it for display, but we could remove it here if needed
        pass

    return render_template(
        'index.html',
        result=True,
        imagepath='/' + save_path,
        prediction=prediction
    )


# ---------------- MAIN ----------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(debug=debug, host="0.0.0.0", port=port)
