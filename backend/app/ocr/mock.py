from datetime import date

from app.ocr.base import OcrDraft
from app.schemas.ticket import PlayLineIn


def _mains_from_seed(seed: int) -> list[int]:
    """Deterministically build 5 distinct numbers in 1..69 from ``seed``.

    Uses a linear-congruential-ish walk so different seeds usually differ,
    while always yielding a valid Powerball main set.
    """
    mains: list[int] = []
    x = (seed * 2654435761) & 0xFFFFFFFF
    while len(mains) < 5:
        x = (x * 1103515245 + 12345) & 0x7FFFFFFF
        n = (x % 69) + 1  # 1..69
        if n not in mains:
            mains.append(n)
    return mains


def _special_from_seed(seed: int) -> int:
    x = (seed * 40503 + 7) & 0x7FFFFFFF
    return (x % 26) + 1  # 1..26


class MockOcrProvider:
    """Deterministic mock OCR provider.

    Returns a plausible, always-VALID Powerball draft so the scan/confirm flow
    works with no API key. Numbers vary by the image byte length so repeated
    scans of different photos are not identical, but the same input always
    yields the same draft.
    """

    def extract(self, image_bytes: bytes, filename: str) -> OcrDraft:
        seed = len(image_bytes)

        line1_mains = _mains_from_seed(seed + 1)
        line1_special = _special_from_seed(seed + 1)
        line2_mains = _mains_from_seed(seed + 2)
        line2_special = _special_from_seed(seed + 2)

        lines = [
            PlayLineIn(
                main_numbers=line1_mains,
                special_number=line1_special,
                wager_cents=200,
                is_quick_pick=False,
            ),
            PlayLineIn(
                main_numbers=line2_mains,
                special_number=line2_special,
                wager_cents=200,
                is_quick_pick=True,  # quick-pick line
            ),
        ]

        confidence = {
            "game_key": 0.97,
            "purchase_date": 0.88,
            "num_draws": 0.9,
            "add_ons": 0.82,
            "line_0": 0.93,
            "line_1": 0.86,
        }

        return OcrDraft(
            game_key="powerball",
            purchase_date=date.today(),
            num_draws=1,
            add_ons={"power_play": True},
            lines=lines,
            confidence=confidence,
            flags=[],
            raw_text=(
                "POWERBALL\n"
                f"{' '.join(f'{n:02d}' for n in line1_mains)}  "
                f"PB {line1_special:02d}\n"
                f"{' '.join(f'{n:02d}' for n in line2_mains)}  "
                f"PB {line2_special:02d}  QP\n"
                "POWER PLAY"
            ),
        )
