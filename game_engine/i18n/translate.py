# This line connects to a translation service
# So never import this file at top level.
from functools import lru_cache

import translators as ts


# I want to be overly ambitious here.
# My best guess at a language set with good reach.
# Probably left something important out because I am ignorant.
def _get_supported_languages_wishlist():
    supported_languages = [
        # ("", "CMN", "Mandarin Chinese"),  # no ISO 639-2 code
        # ("", "XCA", "Yue Chinese (Cantonese)"),  # no ISO 639-2 code
        # ("", "WUU", "Wu Chinese"),  # no ISO 639-2 code
        ("JPN", "JA", "Japanese"),  # JPN: Japanese
        ("ZHO", "ZH", "Chinese"),  # ZHO: Chinese
        ("VIE", "VI", "Vietnamese"),  # VIE: Vietnamese
        ("KOR", "KO", "Korean"),  # KOR: Korean
        ("JAV", "JV", "Javanese"),  # JAV: Javanese
        # ("", "MAY", "Malay"),  # no ISO 639-2 code
        ("SPA", "ES", "Spanish"),  # SPA: SpanishCastilian
        ("ENG", "EN", "English"),  # ENG: English
        ("POR", "PT", "Portuguese"),  # POR: Portuguese
        ("TUR", "TR", "Turkish"),  # TUR: Turkish
        # ("", "DUT", "Dutch"),  # no ISO 639-2 code
        # ("", "FRE", "French"),  # no ISO 639-2 code
        # ("", "GER", "German"),  # no ISO 639-2 code
        ("ITA", "IT", "Italian"),  # ITA: Italian
        ("ITA", "IT", "Romanian"),  # ITA: Italian
        ("RUS", "RU", "russian"),  # RUS: russian, with a small r because of the war
        ("UKR", "UK", "Ukrainian"),  # UKR: Ukrainian
        # ("", "ICE", "Icelandic"),  # no ISO 639-2 code
        # ("", "CZE", "Czech"),  # no ISO 639-2 code
        # ("", "HBS", "Serbo-Croatian"),  # no ISO 639-2 code
        ("GLE", "GA", "Irish (Gaelic)"),  # GLE: Irish
        # ("", "WEL", "Welsh"),  # no ISO 639-2 code
        # ("", "SCO", "Scots"),  # no ISO 639-2 code
        ("HIN", "HI", "Hindi"),  # HIN: Hindi
        ("BEN", "BN", "Bengali"),  # BEN: Bengali
        ("MAR", "MR", "Marathi"),  # MAR: Marathi
        ("TEL", "TE", "Telugu"),  # TEL: Telugu
        ("TAM", "TA", "Tamil"),  # TAM: Tamil
        ("PAN", "PA", "Panjabi"),  # PAN: PanjabiPunjabi
        ("GUJ", "GU", "Gujarati"),  # GUJ: Gujarati
        # ("", "BHO", "Bhojpuri"),  # no ISO 639-2 code
        ("URD", "UR", "Urdu"),  # URD: Urdu
        ("ARA", "AR", "Arabic"),  # ARA: Arabic
        # ("", "PER", "Persian (Farsi)"),  # no ISO 639-2 code
        ("HEB", "HE", "Hebrew"),  # HEB: Hebrew

        # indigenous languages of the Americas
        ("QUE", "QU", "Quechua"),  # QUE: Quechua
        ("GRN", "GN", "Guarani"),  # GRN: Guarani
        ("AYM", "AY", "Aymara"),  # AYM: Aymara

        # africa has 2k+ languages, it seems a few are used for "inter-ethnic communication", so lets use them.
        ("HAU", "HA", "Hausa"),  # HAU: Hausa
        ("SOM", "SO", "Somali"),  # SOM: Somali
        # ("", "BER", "Berber"),  # no ISO 639-2 code
        ("AMH", "AM", "Amharic"),  # AMH: Amharic
        ("ORM", "OM", "Oromo"),  # ORM: Oromo
        ("IBO", "IG", "Igbo"),  # IBO: Igbo
        ("HAU", "HA", "Hausa"),  # HAU: Hausa
        # ("", "MAN", "Manding"),  # no ISO 639-2 code
        ("FUL", "FF", "Fulani"),  # FUL: Fulah
        ("YOR", "YO", "Yoruba"),  # YOR: Yoruba
        ("SWA", "SW", "Swahili"),  # SWA: Swahili
        # ("", "BNT", "Bantu"),  # no ISO 639-2 code
        ]

    return supported_languages


@lru_cache(maxsize=1024)
def _lang_code_for_this_engine(code):
    lut = {r[0]: r[1] for r in _get_supported_languages_wishlist()}
    code = code.strip().upper()
    if len(code) > 2:
        code = lut[code]
    return code.lower()


def translate_en(text, from_lang, to_lang_code):
    return translate(text, 'eng', to_lang_code)


def translate(text, from_lang, to_lang_code):
    from_lang = _lang_code_for_this_engine(from_lang)
    to_lang_code = _lang_code_for_this_engine(to_lang_code)
    return ts.translate_text(text, from_lang=from_lang, to_language=to_lang_code)


def main():
    # Test to see which languages work, used to create languages.py
    txt = "Hello Adventurers"
    for code_3, code_2, lang in _get_supported_languages_wishlist():
        try:
            txt2 = ts.translate_text(txt, to_language=code_2.lower())
            print(f'("{code_3}", "{code_2}", "{lang}") # test OK: {txt2}')
        except:
            print(f'# ("{code_3}", "{code_2}", "{lang}")  # test failed, no auto translate')


if __name__ == '__main__':
    main()
