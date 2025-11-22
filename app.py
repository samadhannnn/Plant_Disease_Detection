import os
import uuid
import json
import numpy as np
import tensorflow as tf
import gdown
from flask import Flask, render_template, request, redirect, send_from_directory

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
    model = tf.keras.models.load_model(MODEL_PATH)
    print("✅ Model loaded.")
    return model


app = Flask(__name__)
model = load_keras_model()

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
    img = extract_features(image_path)
    pred = model.predict(img)
    idx = int(np.argmax(pred))
    return plant_disease[idx]


@app.route('/upload/', methods=['POST'])
def uploadimage():
    image = request.files.get('img')
    if not image or image.filename == "":
        return redirect('/')

    save_path = f"{UPLOAD_DIR}/temp_{uuid.uuid4().hex}_{image.filename}"
    image.save(save_path)

    prediction = model_predict(save_path)

    return render_template(
        'index.html',
        result=True,
        imagepath='/' + save_path,
        prediction=prediction
    )


# ---------------- MAIN ----------------

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
