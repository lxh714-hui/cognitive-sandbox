from .style_sheet import DARK_STYLESHEET


def apply_theme(application):
    application.setStyle("Fusion")
    application.setStyleSheet(DARK_STYLESHEET)
