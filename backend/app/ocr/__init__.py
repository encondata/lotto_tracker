from app.config import get_settings
from app.ocr.base import OcrDraft, OcrField, OcrProvider
from app.ocr.mock import MockOcrProvider

__all__ = [
    "OcrDraft",
    "OcrField",
    "OcrProvider",
    "MockOcrProvider",
    "get_provider",
]


def get_provider() -> OcrProvider:
    """Return the configured OCR provider.

    Reads ``settings.ocr_provider``. Only the mock provider is wired up for
    now; a real cloud-vision provider will be added later and requires an API
    key.
    """
    provider = get_settings().ocr_provider
    if provider == "mock":
        return MockOcrProvider()
    raise NotImplementedError(
        f"OCR provider '{provider}' is not implemented. Only 'mock' is "
        "available. A real vision provider must be added and configured with "
        "its API key before it can be selected."
    )
