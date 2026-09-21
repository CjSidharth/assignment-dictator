"""PDF page -> PIL image, for feeding to the vision model."""
import pymupdf as fitz
from PIL import Image


def pdf_to_images(pdf_path, dpi: int = 200, max_edge: int = 1600) -> list[Image.Image]:
    doc = fitz.open(str(pdf_path))
    images = []
    for page in doc:
        # get_pixmap() already applies the page's embedded /Rotate value, which covers
        # the common "scanned sideways" case from phone scanning apps.
        # ponytail: no content-based deskew/orientation detection (would need tesseract OSD) —
        # add if pages come in genuinely rotated with no /Rotate flag set.
        pix = page.get_pixmap(dpi=dpi)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        long_edge = max(img.size)
        if long_edge > max_edge:
            scale = max_edge / long_edge
            img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
        images.append(img)
    doc.close()
    return images
