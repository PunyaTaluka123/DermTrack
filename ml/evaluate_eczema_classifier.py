import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, roc_curve
import seaborn as sns
import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import ImageDataGenerator

# === Load Model and Validation Data ===
IMG_SIZE = 224
BATCH_SIZE = 32
model = load_model("eczema_detection_model.h5")  # written by train_eczema_classifier.py

val_dir = "data/eczema/val"

datagen = ImageDataGenerator(rescale=1./255)
val_gen = datagen.flow_from_directory(
    val_dir,
    target_size=(IMG_SIZE, IMG_SIZE),
    batch_size=BATCH_SIZE,
    class_mode="binary",
    shuffle=False
)

# === Get Predictions ===
y_true = val_gen.classes
y_pred_probs = model.predict(val_gen)
y_pred = (y_pred_probs > 0.5).astype("int").flatten()

# === Classification Report ===
print("🔍 Classification Report:")
print(classification_report(y_true, y_pred,
      target_names=list(val_gen.class_indices.keys())))

# === Confusion Matrix ===
cm = confusion_matrix(y_true, y_pred)
plt.figure(figsize=(6, 5))
sns.heatmap(cm, annot=True, fmt="d", xticklabels=val_gen.class_indices.keys(
), yticklabels=val_gen.class_indices.keys())
plt.xlabel("Predicted")
plt.ylabel("Actual")
plt.title("🧠 Confusion Matrix")
plt.show()

# === ROC Curve ===
fpr, tpr, _ = roc_curve(y_true, y_pred_probs)
auc = roc_auc_score(y_true, y_pred_probs)
plt.plot(fpr, tpr, label=f"AUC = {auc:.2f}")
plt.plot([0, 1], [0, 1], 'k--')
plt.xlabel("False Positive Rate")
plt.ylabel("True Positive Rate")
plt.title("🚀 ROC Curve")
plt.legend()
plt.grid(True)
plt.show()
