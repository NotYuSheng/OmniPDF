from PIL import Image
import requests
from io import BytesIO

def get_image_dimensions(url):
    response = requests.get(url)
    img = Image.open(BytesIO(response.content))
    return img.width, img.height