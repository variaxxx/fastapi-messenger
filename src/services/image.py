from io import BytesIO
from typing import Tuple

from fastapi import UploadFile
from PIL import Image


def resize_image(file: UploadFile, size: int = 800) -> Tuple[BytesIO, str]:
    img = Image.open(file.file)

    image_format = img.format
    min_side = min(img.width, img.height)

    left = (img.width - min_side) // 2
    top = (img.height - min_side) // 2
    right = left + min_side
    bottom = top + min_side
    img = img.crop((left, top, right, bottom))

    img: Image = img.resize((size, size), Image.LANCZOS)

    buf = BytesIO()
    img.save(buf, format=image_format, optimize=True, quality=70)
    buf.seek(0)

    return buf, image_format.lower()
