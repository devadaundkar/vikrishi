import requests
from PIL import Image
from django.conf import settings
import io

HUGGINGFACE_API_TOKEN = settings.HUGGINGFACE_API_TOKEN
API_URL = "https://api-inference.huggingface.co/models/google/vit-base-patch16-224"

FARMING_KEYWORDS = ['tractor', 'plough', 'harvester', 'sprayer', 'seed', 'shovel', 'tiller', 'hoe']


def check_if_farming_tool_hf(image_path):
    API_URL = "https://api-inference.huggingface.co/models/google/vit-base-patch16-224"

    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}"}
    with open(image_path, "rb") as f:
        response = requests.post(API_URL, headers=headers, files={"file": f})

    results = response.json()
    if isinstance(results, dict) and results.get("error"):
        return False, "API Error", 0.0

    FARMING_KEYWORDS = [
        'tractor', 'harvester', 'plough', 'sprayer', 'seed', 'shovel',
        'tiller', 'hoe', 'farm', 'vehicle', 'field', 'barn', 'mower',
        'combine', 'machine', 'hay', 'farm machinery', 'agricultural'
    ]

    for result in results:
        label = result["label"].lower()
        score = result["score"]
        if any(keyword in label for keyword in FARMING_KEYWORDS):
            return True, label, score

    # If none match
    top = results[0]
    return False, top["label"].lower(), top["score"]

