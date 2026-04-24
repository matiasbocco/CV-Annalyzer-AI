import io
import re
import pdfplumber


def extract_text(file_bytes: bytes) -> str:
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        pages = [page.extract_text(layout=True) or "" for page in pdf.pages]

    raw = "\n".join(pages)

    # Collapse multiple spaces/tabs into one, then collapse 3+ newlines into 2
    cleaned = re.sub(r"[ \t]+", " ", raw)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()

    words = cleaned.split()
    if len(words) > 12000:
        cleaned = " ".join(words[:12000]) + " [... CV truncated]"

    return cleaned
