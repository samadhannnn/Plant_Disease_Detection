import tensorflow as tf

model = tf.keras.models.load_model(
    "models/plant_disease_recog_model_pwp.keras"
)

model.save(
    "models/model_small.h5",
    include_optimizer=False
)
