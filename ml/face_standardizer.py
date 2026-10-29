import cv2
import numpy as np
import os
import mediapipe as mp
from datetime import datetime

mp_face_mesh = mp.solutions.face_mesh
mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1, min_detection_confidence=0.5, min_tracking_confidence=0.5)
mp_drawing = mp.solutions.drawing_utils


def calc_angle(eye_l, eye_r):
    dx = eye_r[0] - eye_l[0]
    dy = eye_r[1] - eye_l[1]
    angle = np.arctan2(dy, dx) * (180.0 / np.pi)
    return angle


def align_face(img, lm):
    eye_l = [lm[33].x, lm[33].y]
    eye_r = [lm[263].x, lm[263].y]
    h, w, _ = img.shape
    eye_l = np.array([eye_l[0] * w, eye_l[1] * h], dtype=np.float32)
    eye_r = np.array([eye_r[0] * w, eye_r[1] * h], dtype=np.float32)
    angle = calc_angle(eye_l, eye_r)
    center = ((eye_l + eye_r) // 2).astype(int).tolist()
    rot_mat = cv2.getRotationMatrix2D(tuple(center), angle, scale=1.0)
    aligned_img = cv2.warpAffine(img, rot_mat, (w, h))
    f_w = int(abs(eye_r[0] - eye_l[0]) * 2.5)
    f_h = f_w
    f_x = max(0, int(center[0] - f_w // 2))
    f_y = max(0, int(center[1] - f_h // 2))
    std_face = aligned_img[f_y:f_y + f_h, f_x:f_x + f_w]
    std_face = cv2.resize(std_face, (256, 256))
    return std_face


save_dir = "captured_faces"
if not os.path.exists(save_dir):
    os.makedirs(save_dir)

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Could not open video capture.")
    exit()

while cap.isOpened():
    _, img = cap.read()

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    res = mesh.process(img_rgb)

    if res.multi_face_landmarks:
        for lm in res.multi_face_landmarks:
            std_face = align_face(img, lm.landmark)
            cv2.imshow('Standardized Face', std_face)

            if cv2.waitKey(5) & 0xFF == ord('s'):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_path = os.path.join(save_dir, f"face_{timestamp}.png")
                cv2.imwrite(file_path, std_face)
                print(f"Photo saved as {file_path}")

    cv2.imshow('Original Image', img)

    if cv2.waitKey(5) & 0xFF == ord('q'):
        print("Exiting...")
        break

cap.release()
cv2.destroyAllWindows()
