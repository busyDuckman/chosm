import dataclasses
import io
import logging
import os
from typing import List
import json

from PIL import Image

from game_engine.dice import Dice, Roll
from game_engine.game_engine import NPCType, DamageType, NPCBehaviour, Attack
from mam_game.mam_constants import MAMVersion, Platform, MAMFileParseError
from mam_game.mam_file import MAMFile
import helpers.pil_image_helpers as pih
import helpers.stream_helpers as sh


class MonsterDBFile(MAMFile):
    def __init__(self, file_id: int, name: str, monsters: List[NPCType]):
        super().__init__(file_id, name)
        self.monsters = monsters

    def __str__(self):
        return f"Binary File: id={self.file_id} len={len(self.data)}"

    def get_type_name(self):
        return "binary"

    def _get_bake_dict(self):
        info = super()._get_bake_dict()
        # info["width"] = self.width
        # info["height"] = self.height
        # info["num_frames"] = len(self.frames)
        #
        # def anim_dict(a: AnimLoop):
        #     d = asdict(a)
        #     d["fps"] = a.get_fps()
        #     d["seconds_per_loop"] = a.get_seconds_per_loop()
        #     return d
        #
        # info["animations"] = [anim_dict(a) for a in self.animations.values()]
        return info

    def _gen_preview_image(self, preview_size) -> Image.Image:
        img = Image.new("RGB", size=(preview_size, preview_size))
        img = pih.annotate(img, "monsters", bottom_text=f"n={len(self.monsters)}")
        return img

    def bake(self, file_path):
        # with open(os.path.join(file_path, "data.bin"), 'wb') as f:
        #     f.write(bytes(self.data))
        super().bake(file_path)


def _get_luts():
    target_pri = {
        0b00010000: "any",
        0b00001111: "all_at_once",
        0b00000000: "knight",
        0b00000001: "paladin",
        0b00000010: "archer",
        0b00000011: "cleric",
        0b00000100: "sorcerer",
        0b00000101: "robber",
        0b00001000: "druid",
        0b00001100: "dwarf",
        0b00001001: "ranger"
    }

    mon_type_lut = {
        0: "UNIQUE",
        1: "ANIMAL",
        2: "INSECT",
        3: "HUMANOID",
        4: "UNDEAD",
        5: "GOLEM",
        6: "DRAGON"
    }

    att_type_lut = {
        0: DamageType.PHYSICAL,  # , Whirlwind, Sewer Stalker, Armadillo, Barbarian...
        1: DamageType.MAGIC,  # Mok Heretic, Onyx Golem, Power Lich, Sorceress...
        2: DamageType.FIRE,  # Green Dragon, Beholder Bat, Fire Blower, Lava Dweller...
        3: DamageType.ELECTRICAL,  # Electrapede, Cleric of Mok, Mystic Mage...
        4: DamageType.COLD,  # Cloud Dragon, Phase Dragon, Orc Shaman...
        5: DamageType.POISON,  # Hell Hornet, Octopod, Arachnoid, Screamer...
        6: DamageType.ENERGY,  # Annihilator, Autobot, Energy Dragon, Gamma Gazer...
    }

    att_special_lut = {
        0: None,
        0b00000101: "Poison",      # Mantis Ant, Octopod, Arachnoid, Screamer
        0b00000111: "Disease",     # Dragon Mummy, Rooka
        0b00001000: "Insane",      # Iguanasaurus, Sewer Hag
        0b00001001: "Sleep",       # Orc Shaman, Vampire Lord, Shaalth
        0b00001010: "Curse Items",  # Higher Mummy, Royal Vampire
        0b00001011: "AOE",         # Sand Flower, Harpy (damage to players standing next to the target)
        0b00001100: "Drain SP",    # Onyx Golem, Coven Leader, Phase Mummy
        0b00001110: "Paralyze",    # Electrapede, Morgana
        0b00001111: "Knock Unconscious",  # Giant, Power Lich, Gurodel
        0b00010000: "Confuse",     # Whirlwind
        0b00010001: "Break Weapon",  # Armadillo
        0b00010010: "Weakness",    # Hell Hornet, Vampire
        0b00010011: "Eradicate",   # Skeletal Lich, Mega Dragon, Vampire King
        0b00010100: "Age",         # Minotaur, Killer Cobra, Ghost Mummy
        0b00010101: "Kill",        # Doom Knight, Sandro, Ct. Blackfang
        0b00010110: "Stone",       # Gorgon, Medusa Sprite
        13: "Curse Player",        # Killer Sprite, Tomb Terror, Head Witch
    }

    #TODO: These are for modifing the sprite (pal rotation)
    sprite_sfx_lut = {
        0: None,
        6: "",   # Ghost Mummy
        7: "",   # Energy Dragon, Mega Dragon, Phase Mummy
        10: "",  # Phase Dragon, Gargoyle, Onyx Golem, Coven Leader, Doom Knight, Sandro, Shaalth, Morgana, Ct.
                 # Blackfang, Yog
        11: "",  # Mega Mage, Barkman
        14: "",  # Master Thief

        # clouds
        # 5: "",  # Cult Leader
        # 6: "",  # Spirit Bones, Polter-Fool, Ghost Rider
        # 7: "",  # Yak Master
        # 8: "",  # Head Witch, Count Draco
        # 9: "",  # Guardian
        # 12: "",  # Guardian Asp
        # 14: "",  # Robber Boss, Captain Yang, King's Guard

    }

    return target_pri, mon_type_lut, att_type_lut, att_special_lut


def load_monster_database_file(file_id: int, file_name: str, data: List,
                  ver: MAMVersion, platform: Platform) -> MonsterDBFile:
    if len(data) == 0:
        raise MAMFileParseError(file_id, file_name, "Monster file was empty")
    if len(data) % 60 != 0:
        raise MAMFileParseError(file_id, file_name, "Monster file must be a multiple of 60byte records")

    target_pri, mon_type_lut, att_type_lut, att_special_lut = _get_luts()

    f = io.BytesIO(bytearray(data))

    monsters = []
    num_monsters = len(data) // 60
    logging.info(f"Loading monsters: n={num_monsters}, file={file_name}")
    for i in range(num_monsters):
        npc_name = sh.read_string(f, size=16)  # 16 bytes name
        # Referencing a binary dump of the 35 byte stats record for the "whirlwind" monster
        # to infer the record from known stats

        # first 10 bytes
        # 90 D0 03 00 E8 03 0A FA 01 0F
        # XP_________ HP___ AC s  ar F1
        # 250000      1000  10 250 1 all
        xp, hp, ac, speed, att_per_round, hates = sh.read_list(f, "uint32,uint16,byte,byte,byte,byte")

        if hates in target_pri:
            hates = target_pri[hates]
        else:
            logging.error(f"unknown target priority file={file_name}, npc={npc_name}, hates={hates:08b}")
            hates = "all"

        # next 8 bytes
        # 05 00 64 00 10 FA 00 00
        # nd___ dn F1 F2 hc F3 F4
        # 5     100      250
        num_dice, dice_sides, attack_type, attack_special, hit_chance, ranged_attack, type_id \
            = sh.read_list(f, "uint16,byte,byte,byte,byte,byte,byte")

        if not (0 < num_dice <= 5000):
            logging.error(f"invalid number of dice: file={file_name}, npc={npc_name}, num_dice={num_dice}")

        if dice_sides == 0:
            logging.error(f"invalid dice sides: file={file_name}, npc={npc_name}, dice_sides={dice_sides}")

        # if hit_chance == 0:
        #     logging.error(f"Bad hit chance: file={file_name}, npc={npc_name}, hit_chance={hit_chance}")
        # hit_chance = hit_chance / 255
        # TODO: No idea on hot chance

        if attack_special not in att_special_lut:
            logging.error(f"unknown special attack: file={file_name}, npc={npc_name}, attack_special={attack_special}")
            attack_special = att_special_lut[0]
        else:
            attack_special = att_special_lut[attack_special]

        if attack_type not in att_type_lut:
            logging.error(f"unknown attack type: file={file_name}, npc={npc_name}, attack_type={attack_type}")
            attack_type = att_type_lut[0]
        else:
            attack_type = att_type_lut[attack_type]

        if ranged_attack not in [0, 1]:
            logging.error(f"unknown ranged_attack: file={file_name}, npc={npc_name}, ranged_attack={ranged_attack}")
        ranged_attack = bool(ranged_attack)

        if type_id not in mon_type_lut:
            logging.error(f"unknown monster type: file={file_name}, npc={npc_name}, type_id={type_id}")
            mon_type = mon_type_lut[0]
        else:
            mon_type = mon_type_lut[type_id]

        # next 7 bytes (resistances)
        # 64 64 64 64 00 00 64
        types = [DamageType.FIRE,   DamageType.ELECTRICAL, DamageType.COLD,     DamageType.POISON,
                 DamageType.ENERGY, DamageType.MAGIC,      DamageType.PHYSICAL]
        resistances = {t: sh.read_byte(f) for t in types}

        # last 10 bytes
        # 00 00 00 00 00 00 01 00 00 B0
        # ?  $     💎 %d ✈  sn pp fx 🔊

        unknown, gold, gems, item_chance, flying, sprite_id, \
            ping_pong, anim_fx_id, idle_sfx_id = sh.read_list(f, "byte,uint16,byte,byte,byte,byte,byte,byte,byte")

        # todo: anim_fx_id = sprite_sfx_lut[anim_fx_id]

        if not (0 <= flying <= 1):
            raise MAMFileParseError(file_id, file_name, "flying flag must be 0 or 1")
        flying = bool(flying)

        if unknown != 0:
            logging.warning(f"Unused(?) value[#1] no set: file={file_name}, npc={npc_name}, value={unknown}")

        sh.read_dict(f, [])
        attack_snd = sh.read_string(f, size=8)
        if len(attack_snd) == 0:
            logging.warning(f"no attack sound: file={file_name}, npc={npc_name}, value={unknown}")
        attack_snd += ".voc"

        last_byte = sh.read_byte(f)
        if last_byte != 0:
            logging.warning(f"Unused(?) value[#2] no set: file={file_name}, npc={npc_name}, value={unknown}")
            exit(1)

        behaviour = NPCBehaviour(is_monster=True, can_swim=False, can_walk=True, can_fly=flying,
                                 will_flee=False, target_priority=hates, ranged_attack=ranged_attack)
        stats = dict(hp=hp, ac=ac, speed=speed, att_per_round=att_per_round)
        roll = Roll(Dice(num_dice, dice_sides))
        attack = Attack([(roll, attack_type)], attack_special, hit_chance)

        npc = NPCType(npc_name, type=mon_type, behaviour=behaviour,
                      stats=stats, spells=[], resistance=resistances,
                      attacks=[attack])

        monsters.append(npc)

    return MonsterDBFile(file_id, file_name, monsters)
