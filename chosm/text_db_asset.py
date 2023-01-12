import json
import logging
import os
from dataclasses import dataclass
import time
from textwrap import dedent
from typing import List, Dict

# TODO: Is the upcoming toml support in python 3.11 any better?
import toml

from PIL import Image
from slugify import slugify

from chosm.asset import Asset
from game_engine.i18n.languages import normalise_lang_code, get_supported_languages
from helpers import pil_image_helpers as pih



@dataclass
class Translation:
    text: str
    language_code: str
    is_human_translation: bool

    def __lt__(self, other):
        # sorting a list of Translations should produce the best starting point for auto translation first.
        if not isinstance(other, Translation):
            return NotImplemented

        if self.is_human_translation and not other.is_human_translation:
            return True

        if other.is_human_translation and not self.is_human_translation:
            return False

        # AFAIK english is a good start point for a translation engine.
        this_code = normalise_lang_code(self.language_code).lower()
        other_code = normalise_lang_code(other.language_code).lower()
        if this_code == 'eng':
            return True

        if other_code == 'eng':
            return False

        # just to alphabetical from here
        return this_code < other_code


def expand_translations(t_list: List[Translation]):
    # We never import this at top level, it causes a translation engine to startup and can take a while
    # It's also not needed for running the Chosm server
    from game_engine.i18n.translate import translate

    # Best language for auto translate to the front of the list.
    t_list = normalise_translation_list(t_list)
    reference = t_list[0]
    lang_codes = set([t.language_code for t in t_list])
    lang_codes = [q[0] for q in get_supported_languages() if q[0] not in lang_codes]

    # do any extra translations
    print(f"Translating  {reference.language_code}:", reference.text)
    for code in lang_codes:
        try:
            print("  - " + code + ": ", end='')
            txt = translate(reference.text, from_lang=reference.language_code, to_lang_code=code)
            t_list.append(Translation(txt, code, is_human_translation=False))
            print(txt)
        except:
            print(" -> error translating!")
            logging.error(f"Could not translate: lang={code}")

        time.sleep(0.01)  # a little bit of nettiquette

    return t_list


def normalise_text(text):
    return text.replace("'", '"')  # The ' quote is reserved for the toml


def normalise_translation_list(t_list: List[Translation]):
    return sorted([Translation(normalise_text(t.text), normalise_lang_code(t.language_code), t.is_human_translation) for t in t_list])


def normalise_token(txt: str):
    return slugify(str(txt))[:64]


class TextDBAsset(Asset):
    def __init__(self, file_id: int, name: str, tokens_to_translations: Dict[str, List[Translation]]):
        super().__init__(file_id, name)
        self.tokens_to_translations = {normalise_token(k): normalise_translation_list(v)
                                       for k, v in tokens_to_translations.items()}

    def __str__(self):
        return f"Text Database File: id={self.file_id} num_tokens={len(self.tokens_to_translations)}"

    def get_type_name(self):
        return "text_database"

    def tokens(self):
        return list(self.tokens_to_translations.keys())

    def __getitem__(self, item):
        if isinstance(item, str):
            return self.tokens_to_translations[normalise_token(item)]
        else:
            token, lang = item
            token = normalise_token(token)
            lang = normalise_lang_code(lang)
            search = (t for t in self.tokens_to_translations[token] if t.language_code == lang)
            return next(search)

    def _gen_preview_image(self, preview_size) -> Image.Image:
        img = Image.new("RGB", size=(preview_size, preview_size))
        img = pih.annotate(img, "text i18n", bottom_text=f"n={len(self.tokens_to_translations)}")
        return img

    def _get_bake_dict(self):
        d = super()._get_bake_dict()
        d["num_tokens"] = len(self.tokens_to_translations)
        return d

    def update_translations(self):
        for key, t_list in self.tokens_to_translations.items():
            t_list2 = expand_translations(t_list)
            self.tokens_to_translations[key] = t_list2

    def bake(self, file_path):
        # We never import this at top level, it causes a translation engine to startup and can take a while
        # It's also not needed for running the Chosm server
        from game_engine.i18n.languages import get_supported_languages, normalise_lang_code

        def as_array(t: Translation):
            return [["ai", "human"][t.is_human_translation], t.text]


        # toml output
        d_list = {token: {t.language_code: as_array(t) for t in t_list} for token, t_list in self.tokens_to_translations.items()}
        print(d_list)


        with open(os.path.join(file_path, "dict.toml"), 'w') as f:
            toml.dump(d_list, f)
            # for token, translations in self.tokens_to_translations.items():
            #     f.write(f'[{token}]\n')
            #     for t in translations:
            #         f.write(f"{t.language_code} = " + "'" + t.text + "'\n")
            #     f.write("\n\n")

        super().bake(file_path)


def main():
    toml_string = """
    [test_1]
        eng = ["human", "Press any key to continue."]
        ger = ["ai", "Drücken Sie eine beliebige Taste, um fortzufahren."]
    """
    parsed_toml = toml.loads(dedent(toml_string))
    print(parsed_toml)
    # exit()


    txt = "Hello Adventurers"

    txt2 = """I am Sheltem, Guardian of Terra. Twice now you have defeated my tests, thinking yourself worthy of
     invading my world. Walk carefully then through this third challenge, and take heed your final decision 
     is truly what you desire - for the course of destiny cannot be turned once set in motion"""

    db = {
            "hello_1": [Translation(txt, 'eng', is_human_translation=True)],
            "intro": [Translation(txt2, 'eng', is_human_translation=True)]
          }
    ta_1 = TextDBAsset(123, "test", db)
    ta_1.update_translations()
    print(ta_1["hello_1", "eng"])
    print(ta_1["hello_1"])
    ta_1.bake("../tests/test_data/text_db_bake")


if __name__ == '__main__':
    main()