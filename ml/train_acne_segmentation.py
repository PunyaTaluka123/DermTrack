from ultralytics import YOLO
from multiprocessing import freeze_support


def main():
    model = YOLO('yolov8s-seg.pt')  # or yolov8m-seg.pt
    model.train(data='acne04.yaml',
                epochs=100, imgsz=640, device=0)


if __name__ == '__main__':
    freeze_support()
    main()
