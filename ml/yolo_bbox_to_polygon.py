import os


def bbox_to_polygon(label_path):
    for label_file in os.listdir(label_path):
        if not label_file.endswith(".txt"):
            continue

        file_path = os.path.join(label_path, label_file)
        with open(file_path, "r") as f:
            lines = f.readlines()

        new_lines = []
        for line in lines:
            parts = list(map(float, line.strip().split()))
            if len(parts) != 5:
                continue
            class_id, xc, yc, w, h = parts
            x1 = xc - w / 2
            y1 = yc - h / 2
            x2 = xc + w / 2
            y2 = yc + h / 2

            polygon = [x1, y1, x2, y1, x2, y2, x1, y2]
            polygon = [str(round(x, 6)) for x in polygon]
            new_line = f"{int(class_id)} " + " ".join(polygon)
            new_lines.append(new_line)

        # overwrite the file with polygon version
        with open(file_path, "w") as f:
            f.write("\n".join(new_lines))


# 🔁 Run this on your dataset
label_dirs = [
    "data/acne04/train/labels",
    "data/acne04/valid/labels",
    "data/acne04/test/labels",
]

for path in label_dirs:
    bbox_to_polygon(path)

print("✅ Conversion complete.")
