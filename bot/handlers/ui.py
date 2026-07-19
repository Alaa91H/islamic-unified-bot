"""Shared inline keyboard helpers for navigation controls."""

UI_CLOSE = "ui:close"
UI_NOOP = "ui:noop"
HOME_CALLBACK = "back_to_start"


def bottom_controls_row(
    back_callback: str | None = None,
    *,
    back_label: str = "🔙 رجوع",
    home_callback: str | None = HOME_CALLBACK,
    home_label: str = "🏠 الرئيسية",
    close_callback: str | None = UI_CLOSE,
    close_label: str = "✖️ إغلاق",
):
    """Return one compact bottom row for back/home/close controls."""
    from pyrogram.types import InlineKeyboardButton

    row = []
    if back_callback:
        row.append(InlineKeyboardButton(back_label, callback_data=back_callback))
    if home_callback and home_callback != back_callback:
        row.append(InlineKeyboardButton(home_label, callback_data=home_callback))
    if close_callback:
        row.append(InlineKeyboardButton(close_label, callback_data=close_callback))
    return row


def with_bottom_controls(
    rows,
    back_callback: str | None = None,
    *,
    back_label: str = "🔙 رجوع",
    home_callback: str | None = HOME_CALLBACK,
    home_label: str = "🏠 الرئيسية",
    close_callback: str | None = UI_CLOSE,
    close_label: str = "✖️ إغلاق",
):
    """Append one bottom controls row to existing keyboard rows."""
    controls = bottom_controls_row(
        back_callback,
        back_label=back_label,
        home_callback=home_callback,
        home_label=home_label,
        close_callback=close_callback,
        close_label=close_label,
    )
    return [*rows, controls] if controls else list(rows)


def markup_with_bottom_controls(rows, *args, **kwargs):
    """Build InlineKeyboardMarkup with a consistent bottom controls row."""
    from pyrogram.types import InlineKeyboardMarkup

    return InlineKeyboardMarkup(with_bottom_controls(rows, *args, **kwargs))
