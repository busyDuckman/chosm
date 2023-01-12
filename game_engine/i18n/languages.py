# stuff that has to do with translation, that does not involve a translation engine
from functools import lru_cache


@lru_cache(maxsize=3)
def get_supported_languages():
    supported_languages = [
        ("JPN", "JA", "Japanese"),      # test OK: こんにちは冒険者
        ("ZHO", "ZH", "Chinese"),       # test OK: 你好冒险家
        ("VIE", "VI", "Vietnamese"),    # test OK: Xin chào các nhà thám hiểm
        ("KOR", "KO", "Korean"),        # test OK: 안녕하세요 모험가 여러분
        # ("JAV", "JV", "Javanese"),    # test failed, no auto translate
        ("SPA", "ES", "Spanish"),       # test OK: Hola Aventureros
        ("ENG", "EN", "English"),       # test OK: Hello Adventurers
        ("POR", "PT", "Portuguese"),    # test OK: Olá Aventureiros
        ("TUR", "TR", "Turkish"),       # test OK: Merhaba Maceracılar
        ("ITA", "IT", "Italian"),       # test OK: Ciao avventurieri
        ("ITA", "IT", "Romanian"),      # test OK: Ciao avventurieri
        ("RUS", "RU", "russian"),       # test OK: Привет искатели приключений
        ("UKR", "UK", "Ukrainian"),     # test OK: Привіт, шукачі пригод
        ("GLE", "GA", "Irish (Gaelic),"),  # test OK: Dia duit Eachtránaithe
        ("HIN", "HI", "Hindi"),         # test OK: हैलो एडवेंचरर्स
        ("BEN", "BN", "Bengali"),       # test OK: হ্যালো Adventurers
        ("MAR", "MR", "Marathi"),       # test OK: नमस्ते एडवेंचर्स
        ("TEL", "TE", "Telugu"),        # test OK: హలో అడ్వెంచర్స్
        ("TAM", "TA", "Tamil"),         # test OK: வணக்கம் சாகசக்காரர்கள்
        ("PAN", "PA", "Panjabi"),       # test OK: ਹੈਲੋ ਐਡਵੈਂਚਰਰ
        ("GUJ", "GU", "Gujarati"),      # test OK: હેલો એડવેન્ચરર્સ
        ("URD", "UR", "Urdu"),          # test OK: ہیلو ایڈونچررز
        ("ARA", "AR", "Arabic"),        # test OK: مرحبا المغامرين
        ("HEB", "HE", "Hebrew"),        # test OK: שלום הרפתקנים
        # ("QUE", "QU", "Quechua"),     # test failed, no auto translate
        # ("GRN", "GN", "Guarani"),     # test failed, no auto translate
        # ("AYM", "AY", "Aymara"),      # test failed, no auto translate
        # ("HAU", "HA", "Hausa"),       # test failed, no auto translate
        ("SOM", "SO", "Somali"),        # test OK: Halganka Halganka
        ("AMH", "AM", "Amharic"),       # test OK: ሰላም አድቬንቸርስ
        # ("ORM", "OM", "Oromo"),       # test failed, no auto translate
        # ("IBO", "IG", "Igbo"),        # test failed, no auto translate
        # ("HAU", "HA", "Hausa"),       # test failed, no auto translate
        # ("FUL", "FF", "Fulani"),      # test failed, no auto translate
        # ("YOR", "YO", "Yoruba"),      # test failed, no auto translate
        ("SWA", "SW", "Swahili"),       # test OK: Hello Adventurers
    ]

    # filter to  [("JPN", "Japanese"), ... ]
    return sorted([(q[0], q[2]) for q in supported_languages])


@lru_cache(maxsize=1024)
def normalise_lang_code(code):
    lut = {r[1].upper(): r[0].upper() for r in get_supported_languages()}
    supported = set([r[0].upper() for r in get_supported_languages()])

    code = str(code).strip().upper()[:3]
    if code in supported:
        return code
    if code in lut:
        return lut[code]
    raise ValueError("unsupported language: " + code)




