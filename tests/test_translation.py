import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from core.i18n import t


def test_spanish_translation_loaded():
    assert t("Program", "es") == "Programa"
    assert t("UnknownKey", "es") == "UnknownKey"
