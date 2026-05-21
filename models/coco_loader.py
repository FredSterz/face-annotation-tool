import json


def load_coco_annotations(json_path):
    with open(json_path, "r") as f:
        data = json.load(f)

    return data