import os

from keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.layers import GlobalAveragePooling2D, Dense, Dropout
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.models import Model
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau

from sklearn.metrics import classification_report

# === CONFIG ===
IMG_SIZE = 224
BATCH_SIZE = 32
EPOCHS = 15
DATA_DIR = "data/eczema"  # expects train/ and val/ subfolders, one folder per class

# === DATA GENERATORS ===
train_datagen = ImageDataGenerator(
    rescale=1./255,
    rotation_range=15,
    zoom_range=0.1,
    horizontal_flip=True
)

val_datagen = ImageDataGenerator(rescale=1./255)

train_gen = train_datagen.flow_from_directory(
    os.path.join(DATA_DIR, "train"),
    target_size=(IMG_SIZE, IMG_SIZE),
    batch_size=BATCH_SIZE,
    class_mode="binary"
)

val_gen = val_datagen.flow_from_directory(
    os.path.join(DATA_DIR, "val"),
    target_size=(IMG_SIZE, IMG_SIZE),
    batch_size=BATCH_SIZE,
    class_mode="binary",
    shuffle=False
)

print("Data preprocessing done, going to model")

base_model = MobileNetV2(input_shape=(
    IMG_SIZE, IMG_SIZE, 3), include_top=False, weights='imagenet')
base_model.trainable = False

x = base_model.output  # Should be a KerasTensor
print("x before pooling:", type(x), x)

x = GlobalAveragePooling2D()(x)
x = Dropout(0.3)(x)
x = Dense(64, activation='relu')(x)
output = Dense(1, activation='sigmoid')(x)

model = Model(inputs=base_model.input, outputs=output)


model.compile(optimizer=Adam(learning_rate=1e-4),
              loss='binary_crossentropy', metrics=['accuracy'])

# === CALLBACKS ===
callbacks = [
    EarlyStopping(patience=3, restore_best_weights=True),
    ModelCheckpoint("eczema_model.keras", save_best_only=True),
    ReduceLROnPlateau(monitor='val_loss', factor=0.2, patience=2, min_lr=1e-6)
]

# === INITIAL TRAINING ===
history = model.fit(
    train_gen,
    validation_data=val_gen,
    epochs=EPOCHS,
    callbacks=callbacks
)

# === FINE-TUNING ===
base_model.trainable = True
for layer in base_model.layers[:-20]:
    layer.trainable = False

model.compile(optimizer=Adam(learning_rate=1e-5),
              loss='binary_crossentropy', metrics=['accuracy'])

fine_tune_epochs = 5
model.fit(
    train_gen,
    validation_data=val_gen,
    epochs=fine_tune_epochs,
    callbacks=callbacks
)

# === EVALUATION ===
val_gen.reset()
preds = (model.predict(val_gen) > 0.5).astype("int32")
labels = val_gen.classes
print("\nClassification Report:\n", classification_report(labels, preds))

# === CLASS MAPPING ===
print("\nClass mapping:", train_gen.class_indices)

# === SAVE MODEL ===
model.save("eczema_detection_model.h5")
print("\n✅ Model saved as 'eczema_detection_model.h5'")
