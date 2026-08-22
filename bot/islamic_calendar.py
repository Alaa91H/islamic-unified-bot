"""حسابات التقويم الإسلامية المشتركة بين واجهات Telegram."""

from datetime import date  # noqa: I001

HIJRI_EPOCH = date(622, 7, 16)


def to_hijri(day: date) -> tuple[int, int, int] | None:
    """حوّل التاريخ الميلادي إلى تقدير هجري حسابي محلي بسيط.

    يعيد اليوم والشهر المفهرس من صفر والسنة، أو ``None`` للتواريخ السابقة لعصر
    التقويم المعتمد. تستخدمه الواجهات للاتساق، ولا يقدم ادعاءً برؤية هلال محلية.
    """

    elapsed_days = (day - HIJRI_EPOCH).days
    if elapsed_days < 0:
        return None
    year = elapsed_days // 354 + 1
    month = (elapsed_days % 354) // 29
    day_of_month = (elapsed_days % 29) + 1
    return day_of_month, month, year
