import asyncio
import html
import json
import math
import os
import random
import sqlite3
import string
import textwrap
import time
from datetime import datetime
from io import BytesIO

import requests
from PIL import Image, ImageDraw, ImageFont
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputFile, InputMediaPhoto, Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, ChatMemberHandler, CommandHandler, ContextTypes, filters, MessageHandler


BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BOT_OWNER_ID = int(os.getenv("BOT_OWNER_ID", "0"))
DB_PATH = os.getenv("HEXA_DB_PATH", "hexa_bot.sqlite3")
WELCOME_BANNER = "https://files.catbox.moe/ocawad.jpg"
POKEAPI = "https://pokeapi.co/api/v2/"
EGG_IMAGE = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/lucky-egg.png"

TRAINER_AVATARS = [
    {"name": "Red", "url": "https://play.pokemonshowdown.com/sprites/trainers/red.png"},
    {"name": "Leaf", "url": "https://play.pokemonshowdown.com/sprites/trainers/leaf.png"},
    {"name": "Ethan", "url": "https://play.pokemonshowdown.com/sprites/trainers/ethan.png"},
    {"name": "Lyra", "url": "https://play.pokemonshowdown.com/sprites/trainers/lyra.png"},
    {"name": "Brendan", "url": "https://play.pokemonshowdown.com/sprites/trainers/brendan.png"},
    {"name": "May", "url": "https://play.pokemonshowdown.com/sprites/trainers/may.png"},
    {"name": "Lucas", "url": "https://play.pokemonshowdown.com/sprites/trainers/lucas.png"},
    {"name": "Dawn", "url": "https://play.pokemonshowdown.com/sprites/trainers/dawn.png"},
    {"name": "Hilbert", "url": "https://play.pokemonshowdown.com/sprites/trainers/hilbert.png"},
    {"name": "Hilda", "url": "https://play.pokemonshowdown.com/sprites/trainers/hilda.png"},
    {"name": "Calem", "url": "https://play.pokemonshowdown.com/sprites/trainers/calem.png"},
    {"name": "Serena", "url": "https://play.pokemonshowdown.com/sprites/trainers/serena.png"},
    {"name": "Elio", "url": "https://play.pokemonshowdown.com/sprites/trainers/elio.png"},
    {"name": "Selene", "url": "https://play.pokemonshowdown.com/sprites/trainers/selene.png"},
    {"name": "Victor", "url": "https://play.pokemonshowdown.com/sprites/trainers/victor.png"},
    {"name": "Gloria", "url": "https://play.pokemonshowdown.com/sprites/trainers/gloria.png"},
]
BALLS = {
    "Pokeball": 1.0,
    "Great Ball": 1.35,
    "Ultra Ball": 1.75,
    "Master Ball": 100.0,
    "Safari Ball": 1.25,
    "Net Ball": 1.5,
    "Nest Ball": 1.3,
    "Dusk Ball": 1.6,
    "Quick Ball": 1.5,
    "Repeat Ball": 1.4,
    "Luxury Ball": 1.1,
}

BALL_EMOJI = {
    "Pokeball": "🔴",
    "Great Ball": "🔵",
    "Ultra Ball": "🟡",
    "Safari Ball": "🟢",
    "Net Ball": "🌐",
    "Nest Ball": "🌿",
    "Dusk Ball": "⚫",
    "Quick Ball": "⚡",
    "Repeat Ball": "🔁",
    "Luxury Ball": "💜",
}

BALL_DESC = {
    "Net Ball": "×1.5 vs Water/Bug",
    "Nest Ball": "×1.3 — great vs low-level",
    "Dusk Ball": "×1.6 — great in caves/night",
    "Quick Ball": "×1.5 — best on first throw",
    "Repeat Ball": "×1.4 — great for seen species",
    "Luxury Ball": "×1.1 — raises happiness",
}
REGIONS = {
    "Kanto": (1, 151),
    "Johto": (152, 251),
    "Hoenn": (252, 386),
    "Sinnoh": (387, 493),
    "Unova": (494, 649),
    "Kalos": (650, 721),
    "Alola": (722, 809),
    "Galar": (810, 905),
    "Paldea": (906, 1025),
}
LEGENDARIES = {
    "Kanto": [144, 145, 146, 150, 151],
    "Johto": [243, 244, 245, 249, 250, 251],
    "Hoenn": [377, 378, 379, 380, 381, 382, 383, 384, 385, 386],
    "Sinnoh": [480, 481, 482, 483, 484, 485, 486, 487, 488, 489, 490, 491, 492, 493],
    "Unova": [638, 639, 640, 641, 642, 643, 644, 645, 646, 647, 648, 649],
    "Kalos": [716, 717, 718, 719, 720, 721],
    "Alola": [772, 773, 785, 786, 787, 788, 789, 790, 791, 792, 800, 801, 802, 807],
    "Galar": [888, 889, 890, 891, 892, 893, 894, 895, 896, 897, 898, 905],
    "Paldea": [1001, 1002, 1003, 1004, 1007, 1008, 1024],
}
BABY_POKEMON = [172, 173, 174, 175, 236, 238, 239, 240, 298, 360, 406, 433, 438, 439, 440, 446, 447, 458, 848]
LEGENDARY_IDS = set(pid for ids in LEGENDARIES.values() for pid in ids)
MEGA_STONES = {
    "Venusaurite": "Venusaur → Mega Venusaur",
    "Charizardite X": "Charizard → Mega Charizard X",
    "Charizardite Y": "Charizard → Mega Charizard Y",
    "Blastoisinite": "Blastoise → Mega Blastoise",
    "Lucarionite": "Lucario → Mega Lucario",
    "Gengarite": "Gengar → Mega Gengar",
    "Mewtwonite X": "Mewtwo → Mega Mewtwo X",
    "Mewtwonite Y": "Mewtwo → Mega Mewtwo Y",
    "Gardevoirite": "Gardevoir → Mega Gardevoir",
    "Garchompite": "Garchomp → Mega Garchomp",
    "Absolite": "Absol → Mega Absol",
    "Metagrossite": "Metagross → Mega Metagross",
}

# Mega evolution mapping: base pokemon name -> (mega pokemon name, stat boosts)
MEGA_EVOLUTIONS = {
    "Venusaur": ("venusaur-mega", {"special-attack": 1.2, "special-defense": 1.2}),
    "Charizard": ("charizard-mega-x", {"attack": 1.3, "defense": 1.2}),
    "Blastoise": ("blastoise-mega", {"special-attack": 1.25}),
    "Lucario": ("lucario-mega", {"attack": 1.3, "special-attack": 1.3}),
    "Gengar": ("gengar-mega", {"special-attack": 1.35}),
    "Mewtwo": ("mewtwo-mega-x", {"attack": 1.4, "defense": 1.2}),
    "Gardevoir": ("gardevoir-mega", {"special-attack": 1.3}),
    "Garchomp": ("garchomp-mega", {"attack": 1.3, "special-attack": 1.2}),
    "Absol": ("absol-mega", {"attack": 1.3, "special-attack": 1.2}),
    "Metagross": ("metagross-mega", {"attack": 1.3, "defense": 1.2}),
}

# Stone -> pokemon name that can mega (check if player has right stone for their pokemon)
MEGA_STONE_POKE = {
    "Venusaurite": "Venusaur",
    "Charizardite X": "Charizard",
    "Charizardite Y": "Charizard",
    "Blastoisinite": "Blastoise",
    "Lucarionite": "Lucario",
    "Gengarite": "Gengar",
    "Mewtwonite X": "Mewtwo",
    "Mewtwonite Y": "Mewtwo",
    "Gardevoirite": "Gardevoir",
    "Garchompite": "Garchomp",
    "Absolite": "Absol",
    "Metagrossite": "Metagross",
}

Z_CRYSTALS = {
    "Normalium Z": "Normal-type Z-Move",
    "Firium Z": "Fire-type Z-Move",
    "Waterium Z": "Water-type Z-Move",
    "Electrium Z": "Electric-type Z-Move",
    "Grassium Z": "Grass-type Z-Move",
    "Icium Z": "Ice-type Z-Move",
    "Fightinium Z": "Fighting-type Z-Move",
    "Psychium Z": "Psychic-type Z-Move",
    "Darkinium Z": "Dark-type Z-Move",
    "Dragonium Z": "Dragon-type Z-Move",
    "Fairium Z": "Fairy-type Z-Move",
    "Steelium Z": "Steel-type Z-Move",
}

Z_CRYSTAL_TYPE = {
    "Normalium Z": "normal",
    "Firium Z": "fire",
    "Waterium Z": "water",
    "Electrium Z": "electric",
    "Grassium Z": "grass",
    "Icium Z": "ice",
    "Fightinium Z": "fighting",
    "Psychium Z": "psychic",
    "Darkinium Z": "dark",
    "Dragonium Z": "dragon",
    "Fairium Z": "fairy",
    "Steelium Z": "steel",
}

Z_MOVE_NAMES = {
    "normal": "Breakneck Blitz",
    "fire": "Inferno Overdrive",
    "water": "Hydro Vortex",
    "electric": "Gigavolt Havoc",
    "grass": "Bloom Doom",
    "ice": "Subzero Slammer",
    "fighting": "All-Out Pummeling",
    "psychic": "Shattered Psyche",
    "dark": "Black Hole Eclipse",
    "dragon": "Devastating Drake",
    "fairy": "Twinkle Tackle",
    "steel": "Corkscrew Crash",
}

SHOP_ITEMS = {
    "Pokeball": 50,
    "Great Ball": 120,
    "Ultra Ball": 250,
    "Net Ball": 400,
    "Nest Ball": 350,
    "Dusk Ball": 600,
    "Quick Ball": 450,
    "Repeat Ball": 500,
    "Luxury Ball": 500,
    "Rare Candy": 100,
    "Level Candy": 80,
    "Vitamin": 50,
    "Berry": 50,
    "Fire Stone": 900,
    "Water Stone": 900,
    "Thunder Stone": 900,
    "Leaf Stone": 900,
    "Moon Stone": 1200,
    "Sun Stone": 1200,
    "Ice Stone": 1200,
    "Dawn Stone": 1400,
    "Dusk Stone": 1400,
    "Shiny Stone": 1400,
    "Z Ring": 3000,
    "TM thunderbolt": 1600,
    "TM flamethrower": 1600,
    "TM ice-beam": 1600,
    "TM earthquake": 1800,
    "TM psychic": 1600,
    "Charizardite X": 12000,
    "Lucarionite": 12000,
    "Firium Z": 7000,
    "Waterium Z": 7000,
    "Electrium Z": 7000,
    "Grassium Z": 7000,
}
DROP_ITEMS = [
    "Fire Stone", "Water Stone", "Thunder Stone", "Leaf Stone", "Moon Stone",
    "Sun Stone", "Ice Stone", "Dawn Stone", "Dusk Stone", "Shiny Stone",
    "TM thunderbolt", "TM flamethrower", "TM ice-beam", "TM earthquake",
    "Rare Candy", "Venusaurite", "Charizardite X", "Charizardite Y",
    "Blastoisinite", "Lucarionite", "Gengarite", "Mewtwonite X", "Mewtwonite Y",
    "Gardevoirite", "Garchompite", "Absolite", "Metagrossite",
    "Normalium Z", "Firium Z", "Waterium Z", "Electrium Z", "Grassium Z",
    "Icium Z", "Fightinium Z", "Psychium Z", "Darkinium Z", "Dragonium Z",
    "Fairium Z", "Steelium Z",
]
NATURES = {
    "Hardy": (None, None),
    "Lonely": ("attack", "defense"),
    "Brave": ("attack", "speed"),
    "Adamant": ("attack", "special-attack"),
    "Naughty": ("attack", "special-defense"),
    "Bold": ("defense", "attack"),
    "Relaxed": ("defense", "speed"),
    "Impish": ("defense", "special-attack"),
    "Lax": ("defense", "special-defense"),
    "Timid": ("speed", "attack"),
    "Hasty": ("speed", "defense"),
    "Jolly": ("speed", "special-attack"),
    "Naive": ("speed", "special-defense"),
    "Modest": ("special-attack", "attack"),
    "Mild": ("special-attack", "defense"),
    "Quiet": ("special-attack", "speed"),
    "Rash": ("special-attack", "special-defense"),
    "Calm": ("special-defense", "attack"),
    "Gentle": ("special-defense", "defense"),
    "Sassy": ("special-defense", "speed"),
    "Careful": ("special-defense", "special-attack"),
}
TYPE_CHART = {
    "water": {"fire": 2, "rock": 2, "ground": 2, "grass": 0.5, "dragon": 0.5, "water": 0.5},
    "fire": {"grass": 2, "ice": 2, "bug": 2, "steel": 2, "water": 0.5, "rock": 0.5, "dragon": 0.5, "fire": 0.5},
    "grass": {"water": 2, "rock": 2, "ground": 2, "fire": 0.5, "flying": 0.5, "poison": 0.5, "bug": 0.5, "dragon": 0.5, "steel": 0.5, "grass": 0.5},
    "electric": {"water": 2, "flying": 2, "ground": 0, "dragon": 0.5, "electric": 0.5, "grass": 0.5},
    "ice": {"grass": 2, "ground": 2, "flying": 2, "dragon": 2, "fire": 0.5, "water": 0.5, "ice": 0.5, "steel": 0.5},
    "ground": {"fire": 2, "electric": 2, "poison": 2, "rock": 2, "steel": 2, "flying": 0, "grass": 0.5, "bug": 0.5},
    "fighting": {"normal": 2, "ice": 2, "rock": 2, "dark": 2, "steel": 2, "ghost": 0, "flying": 0.5, "poison": 0.5, "psychic": 0.5, "bug": 0.5, "fairy": 0.5},
    "psychic": {"fighting": 2, "poison": 2, "dark": 0, "psychic": 0.5, "steel": 0.5},
    "dark": {"psychic": 2, "ghost": 2, "fighting": 0.5, "dark": 0.5, "fairy": 0.5},
    "fairy": {"fighting": 2, "dragon": 2, "dark": 2, "fire": 0.5, "poison": 0.5, "steel": 0.5},
    "dragon": {"dragon": 2, "fairy": 0, "steel": 0.5},
    "rock": {"fire": 2, "ice": 2, "flying": 2, "bug": 2, "fighting": 0.5, "ground": 0.5, "steel": 0.5},
    "flying": {"grass": 2, "fighting": 2, "bug": 2, "electric": 0.5, "rock": 0.5, "steel": 0.5},
    "bug": {"grass": 2, "psychic": 2, "dark": 2, "fire": 0.5, "fighting": 0.5, "poison": 0.5, "flying": 0.5, "ghost": 0.5, "steel": 0.5, "fairy": 0.5},
    "poison": {"grass": 2, "fairy": 2, "ground": 0.5, "poison": 0.5, "rock": 0.5, "ghost": 0.5, "steel": 0},
    "ghost": {"psychic": 2, "ghost": 2, "normal": 0, "dark": 0.5},
    "steel": {"ice": 2, "rock": 2, "fairy": 2, "fire": 0.5, "water": 0.5, "electric": 0.5, "steel": 0.5},
    "normal": {"ghost": 0, "rock": 0.5, "steel": 0.5},
}

# Ability effects in battle (simplified)
ABILITY_EFFECTS = {
    "intimidate": {"on_enter": "lower_opponent_attack"},
    "levitate": {"immune_to": ["ground"]},
    "flash-fire": {"immune_to": ["fire"], "boost_type": "fire"},
    "water-absorb": {"immune_to": ["water"]},
    "volt-absorb": {"immune_to": ["electric"]},
    "thick-fat": {"resist": ["fire", "ice"]},
    "adaptability": {"stab_multiplier": 2.0},
    "huge-power": {"attack_multiplier": 2.0},
    "pure-power": {"attack_multiplier": 2.0},
    "speed-boost": {"end_of_turn": "boost_speed"},
    "rough-skin": {"on_contact_damage": 0.125},
    "iron-barbs": {"on_contact_damage": 0.125},
    "magic-guard": {"immune_indirect_damage": True},
    "pixilate": {"convert_normal_to": "fairy", "power_boost": 1.2},
    "aerilate": {"convert_normal_to": "flying", "power_boost": 1.2},
    "refrigerate": {"convert_normal_to": "ice", "power_boost": 1.2},
    "tough-claws": {"contact_power_boost": 1.3},
    "sand-force": {"rock_ground_steel_boost": 1.3},
    "shadow-tag": {},
    "magic-bounce": {},
}


class PokeData:
    def __init__(self):
        self.cache = {}
        self.move_cache = {}
        self.species_cache = {}
        self.ability_cache = {}

    def fetch(self, path_or_url):
        url = path_or_url if path_or_url.startswith("http") else POKEAPI + path_or_url.lstrip("/")
        if url not in self.cache:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            self.cache[url] = response.json()
        return self.cache[url]

    def get_pokemon(self, ident):
        return self.fetch(f"pokemon/{str(ident).lower()}")

    def get_species(self, ident):
        key = str(ident).lower()
        if key not in self.species_cache:
            self.species_cache[key] = self.fetch(f"pokemon-species/{key}")
        return self.species_cache[key]

    def get_base_stats_types_sprites(self, ident):
        data = self.get_pokemon(ident)
        stats = {s["stat"]["name"]: s["base_stat"] for s in data["stats"]}
        types = [t["type"]["name"] for t in data["types"]]
        sprites = data["sprites"]
        other = sprites.get("other", {})
        official = other.get("official-artwork", {}).get("front_default")
        home = other.get("home", {}).get("front_default")
        dream = other.get("dream_world", {}).get("front_default")
        sprite = official or home or dream or sprites.get("front_default")
        abilities = [a["ability"]["name"] for a in data.get("abilities", [])]
        return {
            "id": data["id"],
            "name": data["name"].title(),
            "stats": stats,
            "types": types,
            "sprite": sprite,
            "artwork": sprite,
            "abilities": abilities,
        }

    def get_learnable_moves(self, ident):
        try:
            data = self.get_pokemon(ident)
            return [m["move"]["name"] for m in data.get("moves", [])]
        except Exception:
            return []

    def get_ability_details(self, ability_name):
        key = ability_name.lower()
        if key in self.ability_cache:
            return self.ability_cache[key]
        try:
            data = self.fetch(f"ability/{key}")
            effect = ""
            for entry in data.get("effect_entries", []):
                if entry.get("language", {}).get("name") == "en":
                    effect = entry.get("short_effect", "")
                    break
            self.ability_cache[key] = {"name": ability_name, "effect": effect}
            return self.ability_cache[key]
        except Exception:
            return {"name": ability_name, "effect": ""}

    def get_move_details(self, move_name):
        key = move_name.lower().replace(" ", "-")
        if key not in self.move_cache:
            data = self.fetch(f"move/{key}")
            damage_class = data.get("damage_class", {}).get("name", "status")
            self.move_cache[key] = {
                "name": data["name"],
                "power": data.get("power") or 0,
                "type": data.get("type", {}).get("name", "normal"),
                "category": damage_class,
                "accuracy": data.get("accuracy") or 100,
                "pp": data.get("pp") or 10,
            }
        return self.move_cache[key]

    def get_default_moves(self, ident, level=5):
        data = self.get_pokemon(ident)
        learned = []
        for move in data.get("moves", []):
            for detail in move.get("version_group_details", []):
                if detail.get("move_learn_method", {}).get("name") == "level-up" and detail.get("level_learned_at", 0) <= level:
                    learned.append((detail.get("level_learned_at", 0), move["move"]["name"]))
        learned = sorted(set(learned), reverse=True)
        moves = [m for _, m in learned[:4]]
        if not moves:
            moves = [m["move"]["name"] for m in data.get("moves", [])[:4]]
        return moves[:4] or ["tackle"]

    def calculate_stats(self, base_stats, level, ivs, nature, evs=None):
        stats = {}
        if evs is None:
            evs = {}
        boost, drop = NATURES.get(nature, (None, None))
        for key, base in base_stats.items():
            iv = ivs.get(key, 0)
            ev = evs.get(key, 0)
            if key == "hp":
                stats[key] = math.floor(((2 * base + iv + math.floor(ev / 4)) * level) / 100) + level + 10
            else:
                value = math.floor(((2 * base + iv + math.floor(ev / 4)) * level) / 100) + 5
                if key == boost:
                    value = math.floor(value * 1.1)
                if key == drop:
                    value = math.floor(value * 0.9)
                stats[key] = max(1, value)
        return stats

    def pokemon_id_by_name(self, name):
        return self.get_pokemon(name)["id"]

    def can_evolve(self, pokemon_id, level=None, stone=None):
        info = self.get_base_stats_types_sprites(pokemon_id)
        species = self.get_species(pokemon_id)
        chain = self.fetch(species["evolution_chain"]["url"])["chain"]
        current = info["name"].lower()

        def walk(node):
            if node["species"]["name"] == current:
                for evo in node.get("evolves_to", []):
                    details = evo.get("evolution_details", [{}])[0]
                    item = details.get("item", {})
                    min_level = details.get("min_level")
                    trigger = details.get("trigger", {}).get("name")
                    if stone and item and item.get("name", "").replace("-", " ").lower() == stone.lower().replace("-", " "):
                        return evo["species"]["name"]
                    if level and min_level and level >= min_level:
                        return evo["species"]["name"]
                    if trigger == "level-up" and level and not min_level and level >= 25:
                        return evo["species"]["name"]
                return None
            for evo in node.get("evolves_to", []):
                found = walk(evo)
                if found:
                    return found
            return None

        target = walk(chain)
        if not target:
            return None
        evolved = self.get_pokemon(target)
        return {"id": evolved["id"], "name": evolved["name"].title()}


poke_data = PokeData()


def db():
    connection = sqlite3.connect(DB_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 30000")
    return connection


def init_db():
    with db() as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                coins INTEGER NOT NULL DEFAULT 500,
                current_region TEXT NOT NULL DEFAULT 'Kanto',
                selected_team TEXT NOT NULL DEFAULT '[]',
                collection_sort TEXT NOT NULL DEFAULT 'caught',
                wins INTEGER NOT NULL DEFAULT 0,
                losses INTEGER NOT NULL DEFAULT 0,
                avatar_index INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS inventory (
                user_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, item_name)
            );
            CREATE TABLE IF NOT EXISTS caught_pokemon (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                pokemon_id INTEGER NOT NULL,
                pokemon_name TEXT NOT NULL,
                level INTEGER NOT NULL,
                exp INTEGER NOT NULL DEFAULT 0,
                nickname TEXT,
                nature TEXT NOT NULL,
                iv_hp INTEGER NOT NULL,
                iv_atk INTEGER NOT NULL,
                iv_def INTEGER NOT NULL,
                iv_spa INTEGER NOT NULL,
                iv_spd INTEGER NOT NULL,
                iv_spe INTEGER NOT NULL,
                moves_learned TEXT NOT NULL,
                evs TEXT NOT NULL DEFAULT '{"hp":0,"attack":0,"defense":0,"special-attack":0,"special-defense":0,"speed":0}',
                caught_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS eggs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                egg_type TEXT NOT NULL,
                steps_remaining INTEGER NOT NULL,
                image_url TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS active_encounters (
                user_id INTEGER PRIMARY KEY,
                pokemon_id INTEGER NOT NULL,
                level INTEGER NOT NULL,
                is_safari INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS battle_sessions (
                user_id INTEGER PRIMARY KEY,
                player_poke_id INTEGER NOT NULL,
                opponent_pokemon_id INTEGER NOT NULL,
                opponent_level INTEGER NOT NULL,
                player_hp INTEGER NOT NULL,
                opponent_hp INTEGER NOT NULL,
                is_gym INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS pvp_battles (
                battle_id TEXT PRIMARY KEY,
                challenger_id INTEGER NOT NULL,
                opponent_id INTEGER NOT NULL,
                challenger_poke_id INTEGER NOT NULL,
                opponent_poke_id INTEGER NOT NULL,
                challenger_hp INTEGER NOT NULL,
                opponent_hp INTEGER NOT NULL,
                current_turn INTEGER NOT NULL DEFAULT 0,
                challenger_team TEXT NOT NULL DEFAULT '[]',
                opponent_team TEXT NOT NULL DEFAULT '[]',
                challenger_team_idx INTEGER NOT NULL DEFAULT 0,
                opponent_team_idx INTEGER NOT NULL DEFAULT 0,
                challenger_mega_used INTEGER NOT NULL DEFAULT 0,
                challenger_z_used INTEGER NOT NULL DEFAULT 0,
                opponent_mega_used INTEGER NOT NULL DEFAULT 0,
                opponent_z_used INTEGER NOT NULL DEFAULT 0,
                challenger_transformed INTEGER NOT NULL DEFAULT 0,
                opponent_transformed INTEGER NOT NULL DEFAULT 0,
                chat_id INTEGER NOT NULL,
                message_id INTEGER,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS battle_challenges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                challenger_id INTEGER NOT NULL,
                opponent_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                message_id INTEGER,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS trade_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user_id INTEGER NOT NULL,
                to_user_id INTEGER NOT NULL,
                from_poke_id INTEGER NOT NULL,
                to_poke_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS bot_groups (
                chat_id INTEGER PRIMARY KEY,
                title TEXT,
                added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS redeem_codes (
                code TEXT PRIMARY KEY,
                rewards TEXT NOT NULL,
                max_uses INTEGER NOT NULL DEFAULT 1,
                used_by TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER NOT NULL,
                referred_id INTEGER NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        for col, definition in [
            ("wins", "INTEGER NOT NULL DEFAULT 0"),
            ("losses", "INTEGER NOT NULL DEFAULT 0"),
            ("avatar_index", "INTEGER NOT NULL DEFAULT 0"),
        ]:
            try:
                conn.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")
            except Exception:
                pass
        try:
            conn.execute(
                "ALTER TABLE caught_pokemon ADD COLUMN evs TEXT NOT NULL DEFAULT "
                "'{\"hp\":0,\"attack\":0,\"defense\":0,\"special-attack\":0,\"special-defense\":0,\"speed\":0}'"
            )
        except Exception:
            pass


def save_group(chat_id, title=""):
    with db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO bot_groups (chat_id, title) VALUES (?, ?)",
            (chat_id, title or ""),
        )


def remove_group(chat_id):
    with db() as conn:
        conn.execute("DELETE FROM bot_groups WHERE chat_id = ?", (chat_id,))


def get_all_groups():
    with db() as conn:
        return conn.execute("SELECT chat_id FROM bot_groups").fetchall()


def get_all_user_ids():
    with db() as conn:
        return conn.execute("SELECT user_id FROM users").fetchall()


def create_redeem_code(code, rewards_json, max_uses=1):
    with db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO redeem_codes (code, rewards, max_uses, used_by) VALUES (?, ?, ?, '[]')",
            (code, rewards_json, max_uses),
        )


def get_redeem_code(code):
    with db() as conn:
        return conn.execute("SELECT * FROM redeem_codes WHERE code = ?", (code.upper(),)).fetchone()


def mark_code_used(code, user_id):
    row = get_redeem_code(code)
    if not row:
        return False
    used_by = json.loads(row["used_by"])
    used_by.append(user_id)
    with db() as conn:
        conn.execute("UPDATE redeem_codes SET used_by = ? WHERE code = ?", (json.dumps(used_by), code.upper()))
    return True


def add_user(user_id, name):
    with db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id, name, coins, current_region, selected_team) VALUES (?, ?, 500, 'Kanto', '[]')",
            (user_id, name),
        )


def get_user(user_id):
    with db() as conn:
        return conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()


def update_user(user_id, **fields):
    if not fields:
        return
    keys = ", ".join([f"{k} = ?" for k in fields])
    values = list(fields.values()) + [user_id]
    with db() as conn:
        conn.execute(f"UPDATE users SET {keys} WHERE user_id = ?", values)


def add_item(user_id, item, quantity):
    with db() as conn:
        conn.execute(
            """
            INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, ?)
            ON CONFLICT(user_id, item_name) DO UPDATE SET quantity = MAX(0, quantity + excluded.quantity)
            """,
            (user_id, item, quantity),
        )


def get_item_qty(user_id, item):
    with db() as conn:
        row = conn.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item)).fetchone()
        return row["quantity"] if row else 0


def use_item(user_id, item, quantity=1):
    if get_item_qty(user_id, item) < quantity:
        return False
    add_item(user_id, item, -quantity)
    return True


def add_caught_pokemon_custom(user_id, pokemon_id, pokemon_name, level, nature, ivs, nickname=None):
    moves = poke_data.get_default_moves(pokemon_id, level)
    with db() as conn:
        cur = conn.execute(
            """
            INSERT INTO caught_pokemon
            (user_id, pokemon_id, pokemon_name, level, exp, nickname, nature, iv_hp, iv_atk, iv_def, iv_spa, iv_spd, iv_spe, moves_learned)
            VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id, pokemon_id, pokemon_name, level, nickname, nature,
                ivs[0], ivs[1], ivs[2], ivs[3], ivs[4], ivs[5],
                json.dumps(moves),
            ),
        )
        return cur.lastrowid


def add_caught_pokemon(user_id, pokemon_id, level=5, nickname=None, high_ivs=False):
    info = poke_data.get_base_stats_types_sprites(pokemon_id)
    nature = random.choice(list(NATURES.keys()))
    low = 20 if high_ivs else 0
    ivs = {
        "hp": random.randint(low, 31),
        "attack": random.randint(low, 31),
        "defense": random.randint(low, 31),
        "special-attack": random.randint(low, 31),
        "special-defense": random.randint(low, 31),
        "speed": random.randint(low, 31),
    }
    moves = poke_data.get_default_moves(pokemon_id, level)
    with db() as conn:
        cur = conn.execute(
            """
            INSERT INTO caught_pokemon
            (user_id, pokemon_id, pokemon_name, level, exp, nickname, nature, iv_hp, iv_atk, iv_def, iv_spa, iv_spd, iv_spe, moves_learned)
            VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                pokemon_id,
                info["name"],
                level,
                nickname,
                nature,
                ivs["hp"],
                ivs["attack"],
                ivs["defense"],
                ivs["special-attack"],
                ivs["special-defense"],
                ivs["speed"],
                json.dumps(moves),
            ),
        )
        return cur.lastrowid


def get_pokemon_row(user_id, poke_id):
    with db() as conn:
        return conn.execute("SELECT * FROM caught_pokemon WHERE user_id = ? AND id = ?", (user_id, poke_id)).fetchone()


def row_ivs(row):
    return {
        "hp": row["iv_hp"],
        "attack": row["iv_atk"],
        "defense": row["iv_def"],
        "special-attack": row["iv_spa"],
        "special-defense": row["iv_spd"],
        "speed": row["iv_spe"],
    }


def iv_total(row):
    return sum(row_ivs(row).values())


EV_STATS = ["hp", "attack", "defense", "special-attack", "special-defense", "speed"]
EV_STAT_LABELS = {
    "hp": "HP",
    "attack": "ATK",
    "defense": "DEF",
    "special-attack": "SP.ATK",
    "special-defense": "SP.DEF",
    "speed": "SPEED",
}
EV_MAX_STAT = 252
EV_MAX_TOTAL = 510


def get_evs(row):
    try:
        evs = json.loads(row["evs"] or "{}")
    except Exception:
        evs = {}
    return {stat: evs.get(stat, 0) for stat in EV_STATS}


def set_evs(caught_id, evs):
    with db() as conn:
        conn.execute("UPDATE caught_pokemon SET evs = ? WHERE id = ?", (json.dumps(evs), caught_id))


def ev_total(evs):
    return sum(evs.values())


def display_name(row):
    return row["nickname"] or row["pokemon_name"]


def ensure_started(update):
    user = update.effective_user
    add_user(user.id, user.full_name or user.first_name or str(user.id))
    return user.id


def get_team_ids(user_id):
    user = get_user(user_id)
    return json.loads(user["selected_team"] or "[]") if user else []


def set_team_ids(user_id, ids):
    update_user(user_id, selected_team=json.dumps(ids[:6]))


def collection_rows(user_id, sort=None):
    user = get_user(user_id)
    sort = sort or (user["collection_sort"] if user else "caught")
    order = "id DESC"
    if sort == "name":
        order = "pokemon_name COLLATE NOCASE ASC"
    if sort == "ivs":
        order = "(iv_hp + iv_atk + iv_def + iv_spa + iv_spd + iv_spe) DESC"
    if sort == "level":
        order = "level DESC"
    with db() as conn:
        return conn.execute(f"SELECT * FROM caught_pokemon WHERE user_id = ? ORDER BY {order}", (user_id,)).fetchall()


def find_owned_pokemon(user_id, query):
    query = query.strip().lower().replace("-", " ")
    if not query:
        return None
    with db() as conn:
        rows = conn.execute("SELECT * FROM caught_pokemon WHERE user_id = ? ORDER BY id DESC", (user_id,)).fetchall()
    for row in rows:
        names = [row["pokemon_name"].lower(), (row["nickname"] or "").lower()]
        if query in names:
            return row
    for row in rows:
        names = [row["pokemon_name"].lower(), (row["nickname"] or "").lower()]
        if any(query in name.replace("-", " ") for name in names if name):
            return row
    return None


def find_all_owned_pokemon(user_id, query):
    query = query.strip().lower().replace("-", " ")
    if not query:
        return []
    with db() as conn:
        rows = conn.execute("SELECT * FROM caught_pokemon WHERE user_id = ? ORDER BY id DESC", (user_id,)).fetchall()
    exact = []
    partial = []
    for row in rows:
        names = [row["pokemon_name"].lower(), (row["nickname"] or "").lower()]
        if query in names:
            exact.append(row)
        elif any(query in name.replace("-", " ") for name in names if name):
            partial.append(row)
    return exact if exact else partial


def decrement_egg_steps(user_id):
    hatched = []
    with db() as conn:
        conn.execute("UPDATE eggs SET steps_remaining = MAX(0, steps_remaining - 1) WHERE user_id = ?", (user_id,))
        rows = conn.execute("SELECT * FROM eggs WHERE user_id = ? AND steps_remaining = 0", (user_id,)).fetchall()
        for row in rows:
            conn.execute("DELETE FROM eggs WHERE id = ?", (row["id"],))
    for row in rows:
        baby = random.choice(BABY_POKEMON)
        caught_id = add_caught_pokemon(user_id, baby, level=random.randint(1, 5), high_ivs=True)
        hatched.append((row["id"], caught_id, poke_data.get_base_stats_types_sprites(baby)["name"]))
    return hatched


def type_multiplier(move_type, defender_types):
    multi = 1.0
    for defender_type in defender_types:
        multi *= TYPE_CHART.get(move_type, {}).get(defender_type, 1)
    return multi


def apply_ability_to_stats(stats, ability_name):
    """Apply ability stat modifications."""
    effects = ABILITY_EFFECTS.get(ability_name, {})
    modified = dict(stats)
    if "attack_multiplier" in effects:
        modified["attack"] = int(modified.get("attack", 0) * effects["attack_multiplier"])
    return modified


def is_immune_due_to_ability(ability_name, move_type):
    effects = ABILITY_EFFECTS.get(ability_name, {})
    return move_type in effects.get("immune_to", [])


def get_contact_damage_ability(ability_name):
    effects = ABILITY_EFFECTS.get(ability_name, {})
    return effects.get("on_contact_damage", 0)


def get_stab_multiplier(ability_name):
    effects = ABILITY_EFFECTS.get(ability_name, {})
    return effects.get("stab_multiplier", 1.5)


def apply_ability_power_modifier(ability_name, move_type, move_category, move_power):
    """Apply ability-based power modifications."""
    effects = ABILITY_EFFECTS.get(ability_name, {})
    modified_type = move_type
    modified_power = move_power
    if "convert_normal_to" in effects and move_type == "normal":
        modified_type = effects["convert_normal_to"]
        modified_power = int(modified_power * effects.get("power_boost", 1.0))
    if "contact_power_boost" in effects and move_category == "physical":
        modified_power = int(modified_power * effects["contact_power_boost"])
    return modified_type, modified_power


def simple_damage(attacker_level, attacker_stats, defender_stats, move, defender_types,
                  attacker_ability=None, defender_ability=None, attacker_types=None):
    move_type = move["type"]
    power = move["power"]
    category = move["category"]

    if category == "status" or power == 0:
        return 0, 1, False

    if defender_ability and is_immune_due_to_ability(defender_ability, move_type):
        return 0, 0, False

    if attacker_ability:
        move_type, power = apply_ability_power_modifier(attacker_ability, move_type, category, power)

    power = max(power, 35)

    attack_key = "special-attack" if category == "special" else "attack"
    defense_key = "special-defense" if category == "special" else "defense"

    atk_stats = dict(attacker_stats)
    if attacker_ability:
        atk_stats = apply_ability_to_stats(atk_stats, attacker_ability)

    multiplier = type_multiplier(move_type, defender_types)

    stab = 1.0
    if attacker_types and move_type in attacker_types:
        stab = get_stab_multiplier(attacker_ability) if attacker_ability else 1.5

    is_crit = random.random() < 0.0625
    crit_mult = 1.5 if is_crit else 1.0

    effective_def = max(1, defender_stats[defense_key])

    base = (((2 * attacker_level / 5 + 2) * power * atk_stats[attack_key] / effective_def) / 50) + 2
    damage = max(1, math.floor(base * multiplier * stab * crit_mult * random.uniform(0.85, 1.0)))

    return damage, multiplier, is_crit


def maybe_drop_reward(user_id):
    drops = []
    text = ""
    if random.random() >= 0.0001:
        return {"text": text, "drops": drops}
    if random.random() < 0.85:
        item = random.choice(DROP_ITEMS)
        add_item(user_id, item, 1)
        text += f"\nFound item: <b>{html.escape(item)}</b>"
        drops.append({"kind": "item", "name": item, "quantity": 1})
    else:
        steps = random.randint(5, 11)
        with db() as conn:
            conn.execute("INSERT INTO eggs (user_id, egg_type, steps_remaining, image_url) VALUES (?, ?, ?, ?)", (user_id, "Mystery Egg", steps, EGG_IMAGE))
        text += f"\nFound a <b>Mystery Egg</b> ({steps} hunts to hatch)"
        drops.append({"kind": "egg", "name": "Mystery Egg", "quantity": 1, "steps": steps})
    return {"text": text, "drops": drops}


def make_bar(current, maximum, size=12):
    current = max(0, min(current, maximum))
    filled = round((current / max(1, maximum)) * size)
    return "█" * filled + "░" * (size - filled)


def fonts():
    try:
        return {
            "title": ImageFont.truetype("DejaVuSans-Bold.ttf", 46),
            "subtitle": ImageFont.truetype("DejaVuSans-Bold.ttf", 30),
            "body": ImageFont.truetype("DejaVuSans.ttf", 25),
            "small": ImageFont.truetype("DejaVuSans.ttf", 20),
        }
    except Exception:
        return {"title": None, "subtitle": None, "body": None, "small": None}


def load_image_from_url(url, size=None, flip=False):
    if not url:
        return None
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content)).convert("RGBA")
        if size:
            img.thumbnail(size, Image.Resampling.LANCZOS)
        if flip:
            img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        return img
    except Exception:
        return None


def load_pokemon_art(info, size=(420, 420), flip=False):
    return load_image_from_url(info.get("artwork"), size, flip)


def image_output(img, filename="image.png"):
    if hasattr(img, "getvalue"):
        img.seek(0)
        return InputFile(img, filename=filename)
    output = BytesIO()
    img.save(output, format="PNG")
    output.seek(0)
    return InputFile(output, filename=filename)


def draw_gradient(draw, width, height, top=(18, 28, 42), bottom=(32, 46, 62)):
    for y in range(height):
        ratio = y / max(1, height - 1)
        color = tuple(int(top[i] * (1 - ratio) + bottom[i] * ratio) for i in range(3))
        draw.line([(0, y), (width, y)], fill=color)


def draw_pill(draw, xy, text, font, fill=(46, 62, 82), outline=(95, 125, 160), text_fill=(245, 250, 255)):
    draw.rounded_rectangle(xy, radius=18, fill=fill, outline=outline, width=2)
    box = draw.textbbox((0, 0), text, font=font)
    draw.text((xy[0] + (xy[2] - xy[0] - (box[2] - box[0])) / 2, xy[1] + (xy[3] - xy[1] - (box[3] - box[1])) / 2 - 2), text, fill=text_fill, font=font)


def draw_hp_bar(draw, x, y, current, maximum, width=380, height=22, color=(80, 220, 130)):
    draw.rounded_rectangle((x, y, x + width, y + height), radius=10, fill=(35, 45, 60))
    ratio = max(0, min(1, current / max(1, maximum)))
    fill_w = int(width * ratio)
    if ratio > 0.5:
        bar_color = (80, 220, 130)
    elif ratio > 0.25:
        bar_color = (220, 200, 50)
    else:
        bar_color = (240, 80, 80)
    if fill_w > 0:
        draw.rounded_rectangle((x, y, x + fill_w, y + height), radius=10, fill=bar_color)


def item_detail(item):
    if item in MEGA_STONES:
        return MEGA_STONES[item]
    if item in Z_CRYSTALS:
        return Z_CRYSTALS[item]
    if item.endswith("Stone"):
        return "Evolution stone"
    if item.startswith("TM "):
        return "Teach this move with /tm"
    if item == "Z Ring":
        return "Needed to use Z-Crystals"
    if item == "Rare Candy":
        return "+3 levels per candy (/candy)"
    if item == "Level Candy":
        return "+1 level per candy (/candy)"
    if item == "Vitamin":
        return "+10 EVs per use, max 252/stat (/vitamin)"
    if item == "Berry":
        return "-10 EVs per use (/berry)"
    return "Added to inventory"


ITEM_SPRITE_OVERRIDES = {
    "Pokeball": "poke-ball",
    "Great Ball": "great-ball",
    "Ultra Ball": "ultra-ball",
    "Master Ball": "master-ball",
    "Safari Ball": "safari-ball",
    "Level Candy": "exp-candy-s",
    "Rare Candy": "rare-candy",
    "Vitamin": "hp-up",
    "Berry": "sitrus-berry",
    "Fire Stone": "fire-stone",
    "Water Stone": "water-stone",
    "Thunder Stone": "thunder-stone",
    "Leaf Stone": "leaf-stone",
    "Moon Stone": "moon-stone",
    "Sun Stone": "sun-stone",
    "Ice Stone": "ice-stone",
    "Dawn Stone": "dawn-stone",
    "Dusk Stone": "dusk-stone",
    "Shiny Stone": "shiny-stone",
    "Venusaurite": "venusaurite",
    "Charizardite X": "charizardite-x",
    "Charizardite Y": "charizardite-y",
    "Blastoisinite": "blastoisinite",
    "Lucarionite": "lucarionite",
    "Gengarite": "gengarite",
    "Mewtwonite X": "mewtwonite-x",
    "Mewtwonite Y": "mewtwonite-y",
    "Gardevoirite": "gardevoirite",
    "Garchompite": "garchompite",
    "Absolite": "absolite",
    "Metagrossite": "metagrossite",
    "Normalium Z": "normalium-z--held",
    "Firium Z": "firium-z--held",
    "Waterium Z": "waterium-z--held",
    "Electrium Z": "electrium-z--held",
    "Grassium Z": "grassium-z--held",
    "Icium Z": "icium-z--held",
    "Fightinium Z": "fightinium-z--held",
    "Psychium Z": "psychium-z--held",
    "Darkinium Z": "darkinium-z--held",
    "Dragonium Z": "dragonium-z--held",
    "Fairium Z": "fairium-z--held",
    "Steelium Z": "steelium-z--held",
    "Z Ring": "z-ring",
    "TM thunderbolt": "tm-electric",
    "TM flamethrower": "tm-fire",
    "TM ice-beam": "tm-ice",
    "TM earthquake": "tm-ground",
    "TM psychic": "tm-psychic",
}


def item_sprite_url(item):
    slug = ITEM_SPRITE_OVERRIDES.get(item)
    if not slug:
        if item.startswith("TM "):
            slug = "tm-normal"
        else:
            slug = item.lower().replace(" ", "-")
    return f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/{slug}.png"


def get_trainer_avatar_url(user_id):
    user = get_user(user_id)
    if not user:
        return None
    idx = user["avatar_index"] or 0
    idx = max(0, min(idx, len(TRAINER_AVATARS) - 1))
    return TRAINER_AVATARS[idx]["url"]


def create_challenge_image(challenger_id, challenger_name, opponent_id, opponent_name,
                           challenger_poke_info, opponent_poke_info):
    """Create a battle challenge image showing both players' DPs and Pokemon."""
    width, height = 1000, 600
    f = fonts()
    img = Image.new("RGB", (width, height), (16, 24, 36))
    draw = ImageDraw.Draw(img)
    draw_gradient(draw, width, height, top=(15, 20, 40), bottom=(40, 28, 70))
    draw.rounded_rectangle((30, 30, width - 30, height - 30), radius=32, outline=(255, 215, 95), width=4)

    # Load trainer avatars
    challenger_avatar = load_image_from_url(get_trainer_avatar_url(challenger_id), size=(120, 160))
    opponent_avatar = load_image_from_url(get_trainer_avatar_url(opponent_id), size=(120, 160))

    # Load pokemon art
    challenger_art = load_pokemon_art(challenger_poke_info, (220, 220), flip=True)
    opponent_art = load_pokemon_art(opponent_poke_info, (220, 220))

    # Left side - challenger
    if challenger_avatar:
        img.paste(challenger_avatar, (60, 80), challenger_avatar)
    if challenger_art:
        img.paste(challenger_art, (190, 100), challenger_art)

    # Right side - opponent
    if opponent_avatar:
        img.paste(opponent_avatar, (width - 180, 80), opponent_avatar)
    if opponent_art:
        img.paste(opponent_art, (width - 410, 100), opponent_art)

    # VS text in center
    draw.text((450, 230), "VS", fill=(255, 220, 50), font=f["title"])

    # Names
    draw.text((60, 50), html.escape(challenger_name), fill=(120, 220, 255), font=f["subtitle"])
    draw.text((width - 300, 50), html.escape(opponent_name), fill=(255, 130, 130), font=f["subtitle"])

    # Pokemon names
    draw.text((60, 330), f"{challenger_poke_info['name']}", fill=(200, 220, 255), font=f["body"])
    draw.text((width - 350, 330), f"{opponent_poke_info['name']}", fill=(255, 200, 200), font=f["body"])

    # Challenge text at bottom
    draw.text((300, 430), "⚔️ BATTLE CHALLENGE ⚔️", fill=(255, 215, 50), font=f["subtitle"])
    draw.text((250, 490), "Tap Accept or Decline below", fill=(200, 200, 200), font=f["body"])

    output = BytesIO()
    img.save(output, format="PNG")
    output.seek(0)
    return output


def create_pvp_battle_image(challenger_poke_info, opponent_poke_info,
                            challenger_hp, challenger_max_hp,
                            opponent_hp, opponent_max_hp,
                            challenger_level, opponent_level,
                            challenger_name="Player", opponent_name="Opponent",
                            challenger_transformed=False, opponent_transformed=False):
    """Create the main PvP battle image with HP bars at top."""
    width, height = 1000, 680
    f = fonts()
    img = Image.new("RGB", (width, height), (16, 24, 36))
    draw = ImageDraw.Draw(img)
    draw_gradient(draw, width, height, top=(12, 22, 36), bottom=(50, 36, 76))
    draw.rounded_rectangle((30, 30, width - 30, height - 30), radius=32, outline=(255, 215, 95), width=4)

    # HP bars at TOP
    # Opponent HP bar (top right)
    opp_name_text = f"ENEMY - {opponent_poke_info['name']} [Lv. {opponent_level}]"
    draw.text((520, 44), opp_name_text, fill=(255, 130, 130), font=f["small"])
    draw.text((520, 68), f"Type: {', '.join(t.title() for t in opponent_poke_info['types'])}", fill=(200, 200, 200), font=f["small"])
    draw_hp_bar(draw, 520, 92, opponent_hp, opponent_max_hp, width=440, height=18, color=(240, 95, 95))
    draw.text((520, 114), f"HP: {opponent_hp}/{opponent_max_hp}", fill=(220, 220, 220), font=f["small"])

    # Player HP bar (top left)
    player_name_text = f"{challenger_name} - {challenger_poke_info['name']} [Lv. {challenger_level}]"
    draw.text((50, 44), player_name_text, fill=(120, 220, 255), font=f["small"])
    draw.text((50, 68), f"Type: {', '.join(t.title() for t in challenger_poke_info['types'])}", fill=(200, 200, 200), font=f["small"])
    draw_hp_bar(draw, 50, 92, challenger_hp, challenger_max_hp, width=440, height=18, color=(80, 220, 130))
    draw.text((50, 114), f"HP: {challenger_hp}/{challenger_max_hp}", fill=(220, 220, 220), font=f["small"])

    # Pokemon art panels
    draw.rounded_rectangle((50, 148, 455, 530), radius=26, fill=(235, 242, 250))
    draw.rounded_rectangle((545, 148, 950, 530), radius=26, fill=(235, 242, 250))

    # Load and place art
    p_art = load_pokemon_art(challenger_poke_info, (340, 330), flip=True)
    o_art = load_pokemon_art(opponent_poke_info, (340, 330))

    if p_art:
        img.paste(p_art, (68 + (360 - p_art.width) // 2, 168 + (330 - p_art.height) // 2), p_art)
    if o_art:
        img.paste(o_art, (568 + (340 - o_art.width) // 2, 168 + (330 - o_art.height) // 2), o_art)

    # Transformation labels
    if challenger_transformed:
        draw.text((80, 510), "⚡ TRANSFORMED!", fill=(255, 200, 50), font=f["small"])
    if opponent_transformed:
        draw.text((560, 510), "⚡ TRANSFORMED!", fill=(255, 200, 50), font=f["small"])

    # VS
    draw.text((465, 320), "VS", fill=(255, 220, 100), font=f["title"])

    output = BytesIO()
    img.save(output, format="PNG")
    output.seek(0)
    return output


def create_win_image(winner_name, winner_id, winner_team_ids, winner_poke_info, winner_poke_hp, winner_poke_max_hp):
    """Create a winner image showing the team with player DP and HP bar."""
    width, height = 1000, 500
    f = fonts()
    img = Image.new("RGB", (width, height), (16, 24, 36))
    draw = ImageDraw.Draw(img)
    draw_gradient(draw, width, height, top=(10, 40, 15), bottom=(20, 80, 30))
    draw.rounded_rectangle((30, 30, width - 30, height - 30), radius=32, outline=(80, 220, 130), width=5)

    # Winner label
    draw.text((50, 50), f"🏆 {winner_name} WINS!", fill=(80, 220, 130), font=f["title"])
    draw.text((50, 110), "Earned 200 PD!", fill=(255, 215, 50), font=f["subtitle"])

    # Player avatar
    avatar_img = load_image_from_url(get_trainer_avatar_url(winner_id), size=(120, 160))
    if avatar_img:
        img.paste(avatar_img, (50, 170), avatar_img)

    # Current pokemon with HP bar
    poke_art = load_pokemon_art(winner_poke_info, (180, 180))
    if poke_art:
        img.paste(poke_art, (200, 160), poke_art)

    draw.text((200, 350), f"{winner_poke_info['name']}", fill=(255, 255, 255), font=f["body"])
    draw_hp_bar(draw, 200, 380, winner_poke_hp, winner_poke_max_hp, width=180, height=16)
    draw.text((200, 400), f"HP: {winner_poke_hp}/{winner_poke_max_hp}", fill=(200, 200, 200), font=f["small"])

    # Show team pokemon mini sprites
    team_x = 420
    draw.text((team_x, 160), "Team:", fill=(255, 215, 50), font=f["body"])
    for i, poke_id in enumerate(winner_team_ids[:6]):
        col = i % 3
        row_i = i // 3
        x = team_x + col * 180
        y = 200 + row_i * 130
        try:
            with db() as conn:
                prow = conn.execute("SELECT * FROM caught_pokemon WHERE id = ?", (poke_id,)).fetchone()
            if prow:
                pinfo = poke_data.get_base_stats_types_sprites(prow["pokemon_id"])
                mini = load_pokemon_art(pinfo, (100, 100))
                if mini:
                    img.paste(mini, (x, y), mini)
                draw.text((x, y + 105), pinfo["name"][:8], fill=(220, 220, 220), font=f["small"])
                draw.text((x, y + 122), f"Lv.{prow['level']}", fill=(180, 180, 180), font=f["small"])
        except Exception:
            pass

    output = BytesIO()
    img.save(output, format="PNG")
    output.seek(0)
    return output


def get_player_mega_stone(user_id, pokemon_name):
    """Check if player has a mega stone for their current pokemon. Returns stone name or None."""
    for stone, poke in MEGA_STONE_POKE.items():
        if poke.lower() == pokemon_name.lower() and get_item_qty(user_id, stone) > 0:
            return stone
    return None


def get_player_z_crystal(user_id, pokemon_types):
    """Check if player has a z-crystal matching their pokemon type. Returns crystal name or None."""
    if get_item_qty(user_id, "Z Ring") <= 0:
        return None
    for crystal, crystal_type in Z_CRYSTAL_TYPE.items():
        if crystal_type in pokemon_types and get_item_qty(user_id, crystal) > 0:
            return crystal
    return None


def get_pvp_battle(battle_id):
    with db() as conn:
        return conn.execute("SELECT * FROM pvp_battles WHERE battle_id = ?", (battle_id,)).fetchone()


def update_pvp_battle(battle_id, **fields):
    if not fields:
        return
    keys = ", ".join([f"{k} = ?" for k in fields])
    values = list(fields.values()) + [battle_id]
    with db() as conn:
        conn.execute(f"UPDATE pvp_battles SET {keys} WHERE battle_id = ?", values)


def get_challenge(challenge_id):
    with db() as conn:
        return conn.execute("SELECT * FROM battle_challenges WHERE id = ?", (challenge_id,)).fetchone()


def build_pvp_battle_text(battle, challenger_row, opponent_row,
                          challenger_info, opponent_info,
                          challenger_name, opponent_name):
    """Build the text for active pvp battle message."""
    challenger_evs = get_evs(challenger_row)
    opponent_evs = get_evs(opponent_row)
    challenger_stats = poke_data.calculate_stats(challenger_info["stats"], challenger_row["level"], row_ivs(challenger_row), challenger_row["nature"], challenger_evs)
    opponent_stats = poke_data.calculate_stats(opponent_info["stats"], opponent_row["level"], row_ivs(opponent_row), opponent_row["nature"], opponent_evs)

    lines = []
    lines.append(f"ENEMY - {html.escape(opponent_info['name'])}  [Lv. {opponent_row['level']}]")
    lines.append(f"Type: {', '.join(t.title() for t in opponent_info['types'])}")
    lines.append(make_bar(battle['opponent_hp'], opponent_stats['hp']))
    lines.append(f"HP: {battle['opponent_hp']}/{opponent_stats['hp']}")
    lines.append("")
    lines.append(f"{html.escape(challenger_name)} - {html.escape(display_name(challenger_row))}  [Lv. {challenger_row['level']}]")
    lines.append(f"Type: {', '.join(t.title() for t in challenger_info['types'])}")
    lines.append(make_bar(battle['challenger_hp'], challenger_stats['hp']))
    lines.append(f"HP: {battle['challenger_hp']}/{challenger_stats['hp']}")
    lines.append("")
    lines.append("Choose your move:")

    return "\n".join(lines)


def build_battle_move_text(battle, my_row, my_info, opp_row, opp_info, is_challenger, my_name):
    """Build the caption for active battle with move details."""
    if is_challenger:
        my_hp = battle["challenger_hp"]
        opp_hp = battle["opponent_hp"]
    else:
        my_hp = battle["opponent_hp"]
        opp_hp = battle["challenger_hp"]

    my_evs = get_evs(my_row)
    opp_evs = get_evs(opp_row)
    my_stats = poke_data.calculate_stats(my_info["stats"], my_row["level"], row_ivs(my_row), my_row["nature"], my_evs)
    opp_stats = poke_data.calculate_stats(opp_info["stats"], opp_row["level"], row_ivs(opp_row), opp_row["nature"], opp_evs)

    moves = json.loads(my_row["moves_learned"])[:4]

    lines = []
    lines.append(f"ENEMY - {html.escape(opp_info['name'])}  [Lv. {opp_row['level']}]")
    lines.append(f"Type: {', '.join(t.title() for t in opp_info['types'])}")
    lines.append(make_bar(opp_hp, opp_stats["hp"]))
    lines.append(f"HP: {opp_hp}/{opp_stats['hp']}")
    lines.append("")
    lines.append(f"{html.escape(my_name)} - {html.escape(display_name(my_row))}  [Lv. {my_row['level']}]")
    lines.append(f"Type: {', '.join(t.title() for t in my_info['types'])}")
    lines.append(make_bar(my_hp, my_stats["hp"]))
    lines.append(f"HP: {my_hp}/{my_stats['hp']}")
    lines.append("")

    TYPE_ICONS = {
        "electric": "⚡", "fire": "🔥", "water": "💧", "grass": "🌿",
        "psychic": "🌟", "fighting": "👊", "dark": "🌑", "dragon": "🐉",
        "ice": "❄️", "ghost": "👻", "poison": "☠️", "ground": "🌍",
        "rock": "🪨", "bug": "🐛", "flying": "🦅", "steel": "⚙️",
        "fairy": "🧚", "normal": "⚪",
    }
    CAT_ICONS = {"physical": "⚔️", "special": "💫", "status": "✨"}
    for move_name in moves:
        try:
            m = poke_data.get_move_details(move_name)
            type_icon = TYPE_ICONS.get(m["type"], "⚪")
            cat_icon = CAT_ICONS.get(m["category"], "")
            pwr = m["power"] if m["power"] else "—"
            acc = m["accuracy"] if m["accuracy"] else "—"
            lines.append(f"● {move_name.replace('-', ' ').title()} {type_icon}{cat_icon} [PP:{m['pp']}]")
            lines.append(f"   Pwr:{pwr}  Acc:{acc}  Type:{m['type'].title()}")
        except Exception:
            lines.append(f"● {move_name.replace('-', ' ').title()}")

    return "\n".join(lines)


def build_pvp_move_keyboard(battle_id, my_row, is_challenger, mega_stone=None, z_crystal=None,
                             mega_used=False, z_used=False, my_team_size=1, my_team_idx=0):
    """Build the keyboard for the current player's turn in PvP battle."""
    moves = json.loads(my_row["moves_learned"])[:4]
    role = "c" if is_challenger else "o"

    rows = []
    # Move buttons (2 per row)
    move_row1 = []
    move_row2 = []
    for i, move_name in enumerate(moves):
        btn = InlineKeyboardButton(
            move_name.replace("-", " ").title(),
            callback_data=f"pvp:{battle_id}:{role}:move:{i}"
        )
        if i < 2:
            move_row1.append(btn)
        else:
            move_row2.append(btn)
    if move_row1:
        rows.append(move_row1)
    if move_row2:
        rows.append(move_row2)

    # Action buttons: Forfeit, Switch, Draw
    action_row = [
        InlineKeyboardButton("Forfeit", callback_data=f"pvp:{battle_id}:{role}:forfeit"),
        InlineKeyboardButton("Switch", callback_data=f"pvp:{battle_id}:{role}:switch"),
        InlineKeyboardButton("Draw", callback_data=f"pvp:{battle_id}:{role}:draw"),
    ]
    rows.append(action_row)

    # Mega/Z-Move buttons if available
    transform_row = []
    if mega_stone and not mega_used:
        transform_row.append(
            InlineKeyboardButton(f"Mega ({mega_stone.split('ite')[0] if 'ite' in mega_stone else mega_stone})",
                                 callback_data=f"pvp:{battle_id}:{role}:mega")
        )
    if z_crystal and not z_used:
        transform_row.append(
            InlineKeyboardButton(f"Z-Move ({z_crystal.split(' Z')[0]})",
                                 callback_data=f"pvp:{battle_id}:{role}:zmove")
        )
    if transform_row:
        rows.append(transform_row)

    return InlineKeyboardMarkup(rows)


def create_reward_image(drop):
    card_w, card_h = 700, 560
    panel_h = 180
    img_area_h = card_h - panel_h
    f = fonts()
    img = Image.new("RGB", (card_w, card_h), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, img_area_h, card_w, card_h), fill=(88, 101, 242))
    draw.rounded_rectangle((0, img_area_h - 28, card_w, img_area_h + 2), radius=28, fill=(88, 101, 242))
    icon = None
    try:
        url = EGG_IMAGE if drop["kind"] == "egg" else item_sprite_url(drop["name"])
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        icon = Image.open(BytesIO(response.content)).convert("RGBA")
        target = 320
        icon.thumbnail((target, target), Image.Resampling.LANCZOS)
    except Exception:
        pass
    if icon:
        ix = (card_w - icon.width) // 2
        iy = (img_area_h - icon.height) // 2
        bg = Image.new("RGBA", img.size, (255, 255, 255, 0))
        bg.paste(icon, (ix, iy), icon)
        img = Image.alpha_composite(img.convert("RGBA"), bg).convert("RGB")
        draw = ImageDraw.Draw(img)
    else:
        draw.ellipse(
            (card_w // 2 - 80, img_area_h // 2 - 80, card_w // 2 + 80, img_area_h // 2 + 80),
            fill=(220, 230, 240),
        )
    name_text = drop["name"]
    if drop["kind"] == "egg":
        detail_text = f"Hatch after {drop['steps']} hunts"
    else:
        detail_text = item_detail(drop["name"])
    qty_text = f"Quantity : {drop['quantity']}"
    panel_top = img_area_h + 10
    draw.text((30, panel_top + 10), name_text, fill=(255, 255, 255), font=f["title"])
    draw.text((30, panel_top + 65), detail_text, fill=(220, 230, 255), font=f["body"])
    draw.text((30, panel_top + 110), qty_text, fill=(255, 255, 255), font=f["subtitle"])
    output = BytesIO()
    img.save(output, format="PNG")
    output.seek(0)
    return output


async def send_reward_photos(message, reward):
    for drop in reward.get("drops", []):
        image = create_reward_image(drop)
        name = drop["name"]
        kind_label = "Item" if drop["kind"] == "item" else "Egg"
        await message.reply_photo(
            InputFile(image, filename=f"reward_{drop['kind']}.png"),
            caption=f"✨ <b>{kind_label} Found: {html.escape(name)}</b>",
            parse_mode=ParseMode.HTML,
        )


def create_hunt_image(info, level, region, title="Wild Pokémon"):
    width, height = 900, 760
    f = fonts()
    img = Image.new("RGB", (width, height), (18, 28, 42))
    draw = ImageDraw.Draw(img)
    draw_gradient(draw, width, height)
    draw.rounded_rectangle((28, 28, width - 28, height - 28), radius=34, outline=(255, 215, 95), width=4)
    draw.rounded_rectangle((70, 70, width - 70, 485), radius=26, fill=(245, 248, 252))
    art = load_pokemon_art(info, (560, 380))
    if art:
        img.paste(art, ((width - art.width) // 2, 92 + (360 - art.height) // 2), art)
    draw.text((70, 520), title, fill=(255, 220, 115), font=f["subtitle"])
    draw.text((70, 565), f"{info['name']} - Lv. {level}", fill=(250, 250, 255), font=f["title"])
    draw.text((70, 625), f"Region: {region} | Types: {', '.join(info['types']).title()}", fill=(210, 225, 245), font=f["body"])
    draw.text((70, 675), "Catch it, defeat it for PD, or run.", fill=(180, 200, 225), font=f["body"])
    output = BytesIO()
    img.save(output, format="PNG")
    output.seek(0)
    return output


def caught_card_caption(row, tab="main"):
    info = poke_data.get_base_stats_types_sprites(row["pokemon_id"])
    ivs = row_ivs(row)
    evs = get_evs(row)
    actual = poke_data.calculate_stats(info["stats"], row["level"], ivs, row["nature"], evs)
    moves = json.loads(row["moves_learned"])
    name = html.escape(display_name(row))
    if tab == "moves":
        lines = [f"<b>{name} Moves</b>"]
        for move_name in moves:
            try:
                move = poke_data.get_move_details(move_name)
                lines.append(
                    f"\n┌ 「 <b>{html.escape(move_name.replace('-', ' ').title())}</b> 」\n"
                    f"├ Type: {html.escape(move['type'].title())}\n"
                    f"├ Power: {move['power']} | Accuracy: {move['accuracy']}\n"
                    f"└ Category: {html.escape(move['category'].title())}"
                )
            except Exception:
                lines.append(f"• {html.escape(move_name.replace('-', ' ').title())}")
        return "\n".join(lines)
    if tab == "ivs":
        ev_total_val = ev_total(evs)
        return (
            f"<b>{name} IVs / EVs</b>\n"
            "Points              IV | EV\n"
            "────────────────────\n"
            f"HP                  {ivs['hp']:2d} | {evs.get('hp', 0)}\n"
            f"Attack              {ivs['attack']:2d} | {evs.get('attack', 0)}\n"
            f"Defense             {ivs['defense']:2d} | {evs.get('defense', 0)}\n"
            f"Sp. Atk             {ivs['special-attack']:2d} | {evs.get('special-attack', 0)}\n"
            f"Sp. Def             {ivs['special-defense']:2d} | {evs.get('special-defense', 0)}\n"
            f"Speed               {ivs['speed']:2d} | {evs.get('speed', 0)}\n"
            "────────────────────\n"
            f"Total              {iv_total(row):3d} | {ev_total_val}"
        )
    if tab == "stats":
        return (
            f"<b>{name} Stats</b>\n"
            f"HP: {actual['hp']}\n"
            f"Attack: {actual['attack']}\n"
            f"Defense: {actual['defense']}\n"
            f"Sp. Atk: {actual['special-attack']}\n"
            f"Sp. Def: {actual['special-defense']}\n"
            f"Speed: {actual['speed']}\n"
            f"Nature: {html.escape(row['nature'])}\n"
            f"IV Total: {iv_total(row)}/186"
        )
    if tab == "evolve":
        return f"<b>{name}</b>\nUse <code>/evolve {row['id']}</code> or <code>/evolve {row['id']} Fire Stone</code>."
    if tab == "nickname":
        return f"<b>{name}</b>\nUse <code>/rename {row['id']} NewName</code> to set a nickname."
    if tab == "release":
        return f"<b>{name}</b>\nRelease is protected for now so you do not delete rare Pokémon by mistake."
    if tab == "relearner":
        return f"<b>{name}</b>\nMove relearn is planned. For now use TMs with <code>/tm {row['id']} move-name</code>."
    return (
        f"<b>{name}</b> - Lv. {row['level']} | Nature: {html.escape(row['nature'])}\n"
        f"Types: [{html.escape(' / '.join(t.title() for t in info['types']))}]\n"
        f"Exp: {row['exp']}\n"
        f"To Next Lv: {max(0, row['level'] * 100 - row['exp'])}\n"
        f"IV Total: {iv_total(row)}/186\n"
        f"Collection ID: <code>{row['id']}</code>"
    )


def caught_card_keyboard(caught_id):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Main", callback_data=f"cardview:main:{caught_id}"),
                InlineKeyboardButton("Moves", callback_data=f"cardview:moves:{caught_id}"),
                InlineKeyboardButton("IVs/EVs", callback_data=f"cardview:ivs:{caught_id}"),
            ],
            [
                InlineKeyboardButton("Stats", callback_data=f"cardview:stats:{caught_id}"),
                InlineKeyboardButton("Evolve", callback_data=f"cardview:evolve:{caught_id}"),
                InlineKeyboardButton("Nickname", callback_data=f"cardview:nickname:{caught_id}"),
            ],
            [
                InlineKeyboardButton("Release", callback_data=f"cardview:release:{caught_id}"),
                InlineKeyboardButton("Relearner", callback_data=f"cardview:relearner:{caught_id}"),
            ],
        ]
    )


def safe_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    incoming_user = update.effective_user
    is_new_user = get_user(incoming_user.id) is None
    user_id = ensure_started(update)
    rows = collection_rows(user_id)
    add_item(user_id, "Pokeball", 5)
    add_item(user_id, "Level Candy", 2)
    keyboard = None
    extra = "You already have a starter. Use /hunt to find wild Pokémon."
    if not rows:
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Bulbasaur", callback_data="starter:1"),
                    InlineKeyboardButton("Charmander", callback_data="starter:4"),
                    InlineKeyboardButton("Squirtle", callback_data="starter:7"),
                ],
                [InlineKeyboardButton("Pikachu", callback_data="starter:25"), InlineKeyboardButton("Eevee", callback_data="starter:133")],
            ]
        )
        extra = "Choose your starter. You also received 5 Pokéballs and 2 Level Candy."
    caption = (
        "<b>Welcome to Hexa-style Pokémon Bot</b>\n\n"
        "Catch Pokémon, collect PD, hatch eggs, buy TMs, evolve, battle, travel by region, and build a team of 6.\n\n"
        f"{extra}\n\n"
        "Commands: /hunt /team /inv /collection /card /battle /shop /travel /safari /profile /top /help"
    )
    try:
        await update.message.reply_photo(WELCOME_BANNER, caption=caption, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    except Exception:
        await update.message.reply_text(caption, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    if is_new_user and context.args:
        ref_arg = context.args[0]
        if ref_arg.startswith("ref_"):
            referrer_id = safe_int(ref_arg[4:])
            if referrer_id and referrer_id != user_id:
                await process_referral(referrer_id, user_id, context)


HELP_BANNER = "https://files.catbox.moe/1kewfx.jpg"

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_started(update)
    text = (
        "<b>⚡ Hexa Bot — Command List</b>\n\n"
        "<b>🌿 Basics</b>\n"
        "/start — register &amp; choose your starter\n"
        "/hunt — find wild Pokémon, PD, items, eggs\n"
        "/safari — 250 PD, 1% legendary chance\n"
        "/run — clear a stuck hunt or battle\n\n"
        "<b>👜 Team &amp; Collection</b>\n"
        "/team — interactive team manager\n"
        "/collection [page] — browse caught Pokémon\n"
        "/slot name|caught|ivs|level — sort collection\n"
        "/card &lt;name or ID&gt; — detailed stats card\n"
        "/rename &lt;ID&gt; &lt;name&gt; — nickname a Pokémon\n"
        "/evolve &lt;ID&gt; [stone] — evolve by level or stone\n"
        "/hatch — hatch ready eggs\n\n"
        "<b>⚔️ Battle</b>\n"
        "/battle — reply to another player in group to challenge them\n"
        "        ↳ Requires /team set first!\n"
        "        ↳ Group only — challenges the replied user\n\n"
        "<b>🧪 Training</b>\n"
        "/candy &lt;name/ID&gt; — level up with candy\n"
        "/vitamin &lt;name/ID&gt; — add EVs to a stat\n"
        "/berry &lt;name/ID&gt; — remove EVs from a stat\n\n"
        "<b>🛍️ Shop &amp; Items</b>\n"
        "/shop — browse item shop\n"
        "/buy &lt;item&gt; &lt;qty&gt; — purchase items\n"
        "/inv — view your inventory\n"
        "/gift &lt;user_id&gt; &lt;amount&gt; — send PD\n\n"
        "<b>🌍 World</b>\n"
        "/travel &lt;region&gt; — change hunt region\n"
        "/trade &lt;user_id&gt; &lt;ID&gt; &lt;ID&gt; — trade Pokémon\n"
        "/trade_accept &lt;id&gt; — accept a trade\n\n"
        "<b>👤 Profile</b>\n"
        "/profile — your trainer profile card\n"
        "/avatar — choose your trainer avatar\n"
        "/top — leaderboards\n"
        "/data &lt;name/dex#&gt; — PokéAPI data\n"
        "/lore &lt;name&gt; — item/Pokémon lore"
    )
    try:
        await update.message.reply_photo(photo=HELP_BANNER)
    except Exception:
        pass
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def starter_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = ensure_started(update)
    if collection_rows(user_id):
        await query.edit_message_caption(caption="You already picked your starter. Use /hunt to continue.", parse_mode=ParseMode.HTML)
        return
    pokemon_id = int(query.data.split(":")[1])
    caught_id = add_caught_pokemon(user_id, pokemon_id, level=5)
    row = get_pokemon_row(user_id, caught_id)
    set_team_ids(user_id, [caught_id])
    await query.edit_message_caption(
        caption=f"Starter chosen: <b>{html.escape(display_name(row))}</b> #{caught_id}\nYour first team slot is set. Use /hunt now.",
        parse_mode=ParseMode.HTML,
    )


async def open_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("/hunt", callback_data="open_menu:hunt"),
            InlineKeyboardButton("/close", callback_data="open_menu:close"),
        ]
    ])
    await update.message.reply_text("Hunt menu opened!", reply_markup=keyboard)


async def close_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hunt menu closed.")


async def open_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data.split(":")[1]
    if action == "hunt":
        await query.edit_message_text("Starting a hunt...\nUse /hunt to encounter a wild Pokémon!")
    elif action == "close":
        await query.edit_message_text("Hunt menu closed.")


async def hunt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = ensure_started(update)
    user = get_user(user_id)
    try:
        hatched = decrement_egg_steps(user_id)
    except Exception:
        hatched = []
    low, high = REGIONS.get(user["current_region"], REGIONS["Kanto"])
    pokemon_id = random.randint(low, high)
    level = random.randint(2, 35)
    try:
        info = poke_data.get_base_stats_types_sprites(pokemon_id)
    except Exception:
        try:
            pokemon_id = random.randint(1, 151)
            info = poke_data.get_base_stats_types_sprites(pokemon_id)
        except Exception:
            await update.message.reply_text("Could not fetch Pokémon data right now. Please try /hunt again.")
            return
    with db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO active_encounters (user_id, pokemon_id, level, is_safari, created_at) VALUES (?, ?, ?, 0, ?)",
            (user_id, pokemon_id, level, int(time.time())),
        )
    egg_text = "".join([f"\nEgg hatched: <b>{html.escape(name)}</b> #{caught_id}" for _, caught_id, name in hatched])
    caption = (
        f"<b>Wild {html.escape(info['name'])}</b> appeared!\n"
        f"Region: {html.escape(user['current_region'])}\n"
        f"Level: {level}\n"
        f"Types: {', '.join(info['types']).title()}\n\n"
        f"Choose Catch or Kill.{egg_text}"
    )
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Catch", callback_data="catch"), InlineKeyboardButton("Kill for PD", callback_data="kill")], [InlineKeyboardButton("Run", callback_data="run")]])
    try:
        image = create_hunt_image(info, level, user["current_region"], "Wild Pokémon Appeared")
        await update.message.reply_photo(InputFile(image, filename="hunt.png"), caption=caption, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    except Exception:
        await update.message.reply_text(caption, parse_mode=ParseMode.HTML, reply_markup=keyboard)


def safari_info_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🌿 Enter Safari Zone", callback_data="safari_zone:enter"),
            InlineKeyboardButton("🚪 Exit Safari Zone", callback_data="safari_zone:exit"),
        ]
    ])


def safari_info_text(user_coins):
    return (
        "🌿 <b>Welcome to Safari Zone</b>\n"
        "You can hunt rare, legendary, and mythical Pokémon here.\n\n"
        "<b>Safari Zone Info:</b>\n"
        "• You get 20 Safari Balls (2× catch rate)\n"
        "• You cannot battle with Pokémon\n"
        "• You cannot use any other Poké Ball\n"
        "• You are automatically kicked out when your Safari Balls run out\n"
        "• Using /exit does not refund anything\n"
        "• You can play Safari once per day\n"
        "• Entering Safari resets the daily entry\n"
        "• Catching a Pokémon is not guaranteed\n\n"
        f"<b>Entry Fee: 200 PD</b>  |  💰 Your PD: <b>{user_coins}</b>\n\n"
        "/enter — Enter Safari Zone\n"
        "/exit — Exit Safari Zone"
    )


async def do_safari_enter(user_id, send_fn):
    user = get_user(user_id)
    today = int(time.time() // 86400)
    last_entry = get_item_qty(user_id, "safari_last_entry")
    if last_entry == today:
        await send_fn("⏳ You've already entered Safari Zone today. Come back tomorrow!")
        return
    if user["coins"] < 200:
        await send_fn(f"❌ You need 200 PD to enter Safari Zone. You have {user['coins']} PD.")
        return
    update_user(user_id, coins=user["coins"] - 200)
    with db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO inventory (user_id, item_name, quantity) VALUES (?, 'Safari Ball', 20)",
            (user_id,),
        )
        conn.execute(
            "INSERT OR REPLACE INTO inventory (user_id, item_name, quantity) VALUES (?, 'safari_last_entry', ?)",
            (user_id, today),
        )
    region = user["current_region"]
    legendary_chance = random.random() < 0.05 and LEGENDARIES.get(region)
    if legendary_chance:
        pokemon_id = random.choice(LEGENDARIES[region])
        legendary = True
    else:
        low, high = REGIONS.get(region, REGIONS["Kanto"])
        pokemon_id = random.randint(low, high)
        legendary = False
    level = random.randint(25, 70) if legendary else random.randint(10, 45)
    info = poke_data.get_base_stats_types_sprites(pokemon_id)
    with db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO active_encounters (user_id, pokemon_id, level, is_safari, created_at) VALUES (?, ?, ?, 1, ?)",
            (user_id, pokemon_id, level, int(time.time())),
        )
    balls_left = get_item_qty(user_id, "Safari Ball")
    caption = (
        f"🌿 <b>Safari Encounter!</b>\n"
        f"{'🌟 Legendary: ' if legendary else ''}<b>{html.escape(info['name'])}</b> appeared!\n"
        f"Level: {level} | Types: {', '.join(info['types']).title()}\n\n"
        f"🎯 Safari Balls remaining: <b>{balls_left}</b>\n"
        "Catch uses Safari Ball logic. Kill is disabled in Safari."
    )
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🎯 Catch", callback_data="catch"),
        InlineKeyboardButton("🏃 Run", callback_data="run"),
    ]])
    image = create_hunt_image(info, level, region, "Safari Zone Encounter")
    await send_fn(caption, image=image, keyboard=keyboard)


async def safari(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = ensure_started(update)
    user = get_user(user_id)
    await update.message.reply_text(safari_info_text(user["coins"]), parse_mode=ParseMode.HTML, reply_markup=safari_info_keyboard())


async def safari_enter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = ensure_started(update)

    async def send_fn(text, image=None, keyboard=None):
        if image:
            await update.message.reply_photo(
                InputFile(image, filename="safari.png"),
                caption=text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
            )
        else:
            await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

    await do_safari_enter(user_id, send_fn)


async def safari_exit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = ensure_started(update)
    with db() as conn:
        conn.execute("DELETE FROM active_encounters WHERE user_id = ? AND is_safari = 1", (user_id,))
        conn.execute(
            "INSERT OR REPLACE INTO inventory (user_id, item_name, quantity) VALUES (?, 'Safari Ball', 0)",
            (user_id,),
        )
    await update.message.reply_text(
        "🚪 You have exited the Safari Zone.\nNo refunds are given for unused Safari Balls.",
        parse_mode=ParseMode.HTML,
    )


async def safari_zone_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = ensure_started(update)
    action = query.data.split(":")[1]

    if action == "exit":
        with db() as conn:
            conn.execute("DELETE FROM active_encounters WHERE user_id = ? AND is_safari = 1", (user_id,))
            conn.execute(
                "INSERT OR REPLACE INTO inventory (user_id, item_name, quantity) VALUES (?, 'Safari Ball', 0)",
                (user_id,),
            )
        await query.edit_message_text(
            "🚪 You have exited the Safari Zone.\nNo refunds are given for unused Safari Balls.",
            parse_mode=ParseMode.HTML,
        )
        return

    async def send_fn(text, image=None, keyboard=None):
        if image:
            try:
                await query.message.reply_photo(
                    InputFile(image, filename="safari.png"),
                    caption=text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard,
                )
            except Exception:
                await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        else:
            try:
                await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=safari_info_keyboard())
            except Exception:
                await query.message.reply_text(text, parse_mode=ParseMode.HTML)

    await do_safari_enter(user_id, send_fn)


async def encounter_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = ensure_started(update)
    action = query.data
    if action == "run":
        with db() as conn:
            conn.execute("DELETE FROM active_encounters WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM battle_sessions WHERE user_id = ?", (user_id,))
        await query.edit_message_caption(caption="You ran away. You are free now.", parse_mode=ParseMode.HTML)
        return
    with db() as conn:
        encounter = conn.execute("SELECT * FROM active_encounters WHERE user_id = ?", (user_id,)).fetchone()
    if not encounter:
        await query.edit_message_caption(caption="No active wild Pokémon. Use /hunt.", parse_mode=ParseMode.HTML)
        return
    try:
        info = poke_data.get_base_stats_types_sprites(encounter["pokemon_id"])
    except Exception:
        with db() as conn:
            conn.execute("DELETE FROM active_encounters WHERE user_id = ?", (user_id,))
        await query.edit_message_caption(caption="Could not load Pokémon data. The encounter was cleared. Use /hunt to try again.", parse_mode=ParseMode.HTML)
        return
    if action == "kill":
        if encounter["is_safari"]:
            await query.edit_message_caption(caption="You cannot kill Pokémon inside Safari. Use Catch or Run.", parse_mode=ParseMode.HTML)
            return
        coins = random.randint(10, 25)
        user = get_user(user_id)
        update_user(user_id, coins=user["coins"] + coins)
        reward = maybe_drop_reward(user_id)
        team = get_team_ids(user_id)
        if team:
            gain_exp(team[0], random.randint(15, 45) + encounter["level"])
        with db() as conn:
            conn.execute("DELETE FROM active_encounters WHERE user_id = ?", (user_id,))
        await query.edit_message_caption(caption=f"You defeated <b>{html.escape(info['name'])}</b> and earned <b>{coins} PD</b>.{reward['text']}", parse_mode=ParseMode.HTML)
        await send_reward_photos(query.message, reward)
        return
    if encounter["is_safari"]:
        if get_item_qty(user_id, "Safari Ball") <= 0:
            with db() as conn:
                conn.execute("DELETE FROM active_encounters WHERE user_id = ?", (user_id,))
            await query.edit_message_caption(caption="You ran out of Safari Balls! You've been escorted out of the Safari Zone.", parse_mode=ParseMode.HTML)
            return
        use_item(user_id, "Safari Ball", 1)
        await do_throw_ball(query, user_id, encounter, info, "Safari Ball")
        return
    player_balls = get_player_balls(user_id)
    if not player_balls:
        await query.edit_message_caption(caption="You have no Pokéballs! Buy some with /shop or /buy Pokeball 5.", parse_mode=ParseMode.HTML)
        return
    lines = [f"<b>Wild {html.escape(info['name'])}</b> — Choose a ball to throw!\n"]
    for ball_name, qty in player_balls:
        emoji = BALL_EMOJI.get(ball_name, "⚪")
        desc = BALL_DESC.get(ball_name, "")
        desc_str = f"  <i>{desc}</i>" if desc else ""
        lines.append(f"{emoji} <b>{html.escape(ball_name)}</b> ×{qty}{desc_str}")
    await query.edit_message_caption(
        caption="\n".join(lines),
        parse_mode=ParseMode.HTML,
        reply_markup=build_ball_picker_keyboard(player_balls),
    )


def best_available_ball(user_id):
    for ball in ["Master Ball", "Dusk Ball", "Ultra Ball", "Net Ball", "Quick Ball", "Repeat Ball", "Great Ball", "Nest Ball", "Luxury Ball", "Pokeball"]:
        if get_item_qty(user_id, ball) > 0:
            return ball
    return "Pokeball"


def get_player_balls(user_id):
    """Return list of (ball_name, qty) for balls the player owns (exclude Safari/Master)."""
    result = []
    for ball in ["Pokeball", "Great Ball", "Ultra Ball", "Net Ball", "Nest Ball", "Dusk Ball", "Quick Ball", "Repeat Ball", "Luxury Ball"]:
        qty = get_item_qty(user_id, ball)
        if qty > 0:
            result.append((ball, qty))
    return result


def build_ball_picker_keyboard(balls):
    """Build inline keyboard for selecting which ball to throw."""
    buttons = []
    row = []
    for i, (ball, qty) in enumerate(balls):
        emoji = BALL_EMOJI.get(ball, "⚪")
        label = f"{emoji} {ball} ×{qty}"
        row.append(InlineKeyboardButton(label, callback_data=f"throw:{ball}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("🏃 Run", callback_data="run")])
    return InlineKeyboardMarkup(buttons)


def gain_exp(caught_id, amount):
    with db() as conn:
        row = conn.execute("SELECT * FROM caught_pokemon WHERE id = ?", (caught_id,)).fetchone()
        if not row:
            return None
        exp = row["exp"] + amount
        level = row["level"]
        while exp >= level * 100:
            exp -= level * 100
            level += 1
        conn.execute("UPDATE caught_pokemon SET exp = ?, level = ? WHERE id = ?", (exp, level, caught_id))
        return level


async def do_throw_ball(query, user_id, encounter, info, ball):
    """Shared logic for throwing a ball at a wild Pokémon."""
    chance = min(0.9, (0.46 * BALLS[ball]) - (encounter["level"] * 0.003))
    if random.random() <= chance:
        try:
            caught_id = add_caught_pokemon(user_id, encounter["pokemon_id"], encounter["level"])
        except Exception:
            with db() as conn:
                conn.execute("DELETE FROM active_encounters WHERE user_id = ?", (user_id,))
            await query.edit_message_caption(
                caption=f"Caught <b>{html.escape(info['name'])}</b> with {html.escape(ball)} but failed to save. Use /hunt to try again.",
                parse_mode=ParseMode.HTML,
            )
            return
        row = get_pokemon_row(user_id, caught_id)
        with db() as conn:
            conn.execute("DELETE FROM active_encounters WHERE user_id = ?", (user_id,))
        await query.edit_message_caption(
            caption=f"Caught <b>{html.escape(info['name'])}</b> with {html.escape(ball)}!\nOpening caught Pokémon card below.",
            parse_mode=ParseMode.HTML,
        )
        try:
            await query.message.reply_photo(
                info["artwork"] or WELCOME_BANNER,
                caption=caught_card_caption(row),
                parse_mode=ParseMode.HTML,
                reply_markup=caught_card_keyboard(caught_id),
            )
        except Exception:
            await query.message.reply_text(
                caught_card_caption(row), parse_mode=ParseMode.HTML, reply_markup=caught_card_keyboard(caught_id)
            )
    else:
        with db() as conn:
            conn.execute("DELETE FROM active_encounters WHERE user_id = ?", (user_id,))
        emoji = BALL_EMOJI.get(ball, "⚪")
        await query.edit_message_caption(
            caption=f"{emoji} Threw a <b>{html.escape(ball)}</b>... but {html.escape(info['name'])} broke free and escaped!",
            parse_mode=ParseMode.HTML,
        )


async def throw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = ensure_started(update)
    ball = query.data[len("throw:"):]
    if ball not in BALLS or ball in ("Safari Ball", "Master Ball"):
        await query.answer("Invalid ball.", show_alert=True)
        return
    with db() as conn:
        encounter = conn.execute("SELECT * FROM active_encounters WHERE user_id = ?", (user_id,)).fetchone()
    if not encounter:
        await query.edit_message_caption(caption="No active wild Pokémon. Use /hunt.", parse_mode=ParseMode.HTML)
        return
    try:
        info = poke_data.get_base_stats_types_sprites(encounter["pokemon_id"])
    except Exception:
        with db() as conn:
            conn.execute("DELETE FROM active_encounters WHERE user_id = ?", (user_id,))
        await query.edit_message_caption(caption="Could not load Pokémon data. The encounter was cleared. Use /hunt to try again.", parse_mode=ParseMode.HTML)
        return
    if not use_item(user_id, ball, 1):
        player_balls = get_player_balls(user_id)
        if not player_balls:
            await query.edit_message_caption(caption="You have no Pokéballs left! Buy more with /shop.", parse_mode=ParseMode.HTML)
            return
        lines = [f"<b>Wild {html.escape(info['name'])}</b> — You don't have that ball! Choose another:\n"]
        for ball_name, qty in player_balls:
            emoji = BALL_EMOJI.get(ball_name, "⚪")
            lines.append(f"{emoji} <b>{html.escape(ball_name)}</b> ×{qty}")
        await query.edit_message_caption(
            caption="\n".join(lines),
            parse_mode=ParseMode.HTML,
            reply_markup=build_ball_picker_keyboard(player_balls),
        )
        return
    await do_throw_ball(query, user_id, encounter, info, ball)


DAILY_CHANNEL = "@pokecrestbotupdate"
DAILY_BOT_USERNAME = "@Pokecrest_bot"
DAILY_COOLDOWN = 86400


async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = ensure_started(update)
    now = int(time.time())
    last_claim = get_item_qty(user_id, "_daily_last_claim")
    time_left = (last_claim + DAILY_COOLDOWN) - now
    if last_claim and time_left > 0:
        hours = time_left // 3600
        minutes = (time_left % 3600) // 60
        await update.message.reply_text(
            f"⏳ You already claimed your daily reward!\nCome back in <b>{hours}h {minutes}m</b>.",
            parse_mode=ParseMode.HTML,
        )
        return
    bio_ok = False
    try:
        chat = await context.bot.get_chat(user_id)
        bio = (chat.bio or "").lower()
        if DAILY_BOT_USERNAME.lower() in bio:
            bio_ok = True
    except Exception:
        pass
    channel_ok = False
    try:
        member = await context.bot.get_chat_member(DAILY_CHANNEL, user_id)
        if member.status in ("member", "administrator", "creator"):
            channel_ok = True
    except Exception:
        pass
    fails = []
    if not bio_ok:
        fails.append(f"• Add <b>{html.escape(DAILY_BOT_USERNAME)}</b> to your Telegram bio")
    if not channel_ok:
        fails.append(f"• Join our channel: {DAILY_CHANNEL}")
    if fails:
        msg = (
            "❌ <b>Daily Reward Requirements Not Met</b>\n\n"
            "To claim your daily reward, you must:\n"
            + "\n".join(fails) +
            "\n\nOnce done, use /daily again!"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return
    user = get_user(user_id)
    pd_reward = 200
    pokeball_reward = 20
    greatball_reward = 10
    ultraball_reward = 5
    update_user(user_id, coins=user["coins"] + pd_reward)
    add_item(user_id, "Pokeball", pokeball_reward)
    add_item(user_id, "Great Ball", greatball_reward)
    add_item(user_id, "Ultra Ball", ultraball_reward)
    with db() as conn:
        conn.execute(
            "INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, '_daily_last_claim', ?) "
            "ON CONFLICT(user_id, item_name) DO UPDATE SET quantity = excluded.quantity",
            (user_id, now),
        )
    await update.message.reply_text(
        f"🎁 <b>Daily Reward Claimed!</b>\n\n"
        f"💰 +{pd_reward} PD\n"
        f"🔴 +{pokeball_reward} Pokéballs\n"
        f"🔵 +{greatball_reward} Great Balls\n"
        f"🟡 +{ultraball_reward} Ultra Balls\n\n"
        f"Come back tomorrow for more!",
        parse_mode=ParseMode.HTML,
    )


REFERRAL_TMS = ["TM thunderbolt", "TM flamethrower", "TM ice-beam", "TM earthquake", "TM psychic"]
REFERRAL_MILESTONES = [
    (1,  {"pd": 1000}),
    (5,  {"pd": 2000, "non_legendary_poke": True}),
    (10, {"pd": 3000, "legendary_poke": True, "random_tm": True}),
    (12, {"mega_stone": True}),
]


def get_referral_count(user_id):
    with db() as conn:
        row = conn.execute("SELECT COUNT(*) as cnt FROM referrals WHERE referrer_id = ?", (user_id,)).fetchone()
        return row["cnt"] if row else 0


def is_already_referred(referred_id):
    with db() as conn:
        row = conn.execute("SELECT id FROM referrals WHERE referred_id = ?", (referred_id,)).fetchone()
        return row is not None


def record_referral(referrer_id, referred_id):
    with db() as conn:
        try:
            conn.execute("INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)", (referrer_id, referred_id))
            return True
        except Exception:
            return False


async def check_referral_milestones(referrer_id, count, context):
    user = get_user(referrer_id)
    if not user:
        return
    for threshold, rewards in REFERRAL_MILESTONES:
        if count < threshold:
            continue
        milestone_key = f"_ref_ms_{threshold}"
        if get_item_qty(referrer_id, milestone_key):
            continue
        add_item(referrer_id, milestone_key, 1)
        lines = [f"🎉 <b>Referral Milestone!</b> You've reached <b>{threshold} referral{'s' if threshold > 1 else ''}!</b>\n"]
        if "pd" in rewards:
            fresh = get_user(referrer_id)
            update_user(referrer_id, coins=fresh["coins"] + rewards["pd"])
            lines.append(f"💰 +{rewards['pd']} PD")
        if rewards.get("non_legendary_poke"):
            non_leg = [i for i in range(1, 906) if i not in LEGENDARY_IDS]
            poke_id = random.choice(non_leg)
            try:
                info = poke_data.get_base_stats_types_sprites(poke_id)
                add_caught_pokemon_custom(
                    referrer_id, poke_id, info["name"], 50,
                    random.choice(list(NATURES.keys())), [31, 31, 31, 31, 31, 31]
                )
                lines.append(f"🌟 <b>{html.escape(info['name'])}</b> with perfect 186 IVs added to your collection!")
            except Exception:
                lines.append("🌟 A bonus Pokémon was added to your collection!")
        if rewards.get("legendary_poke"):
            poke_id = random.choice(list(LEGENDARY_IDS))
            try:
                info = poke_data.get_base_stats_types_sprites(poke_id)
                add_caught_pokemon_custom(
                    referrer_id, poke_id, info["name"], 70,
                    random.choice(list(NATURES.keys())), [31, 31, 31, 31, 31, 31]
                )
                lines.append(f"⭐ Legendary <b>{html.escape(info['name'])}</b> with perfect 186 IVs added!")
            except Exception:
                lines.append("⭐ A legendary Pokémon was added to your collection!")
        if rewards.get("random_tm"):
            tm = random.choice(REFERRAL_TMS)
            add_item(referrer_id, tm, 1)
            lines.append(f"📀 <b>{html.escape(tm)}</b> added to your inventory!")
        if rewards.get("mega_stone"):
            stone = random.choice(list(MEGA_STONES.keys()))
            add_item(referrer_id, stone, 1)
            lines.append(f"💎 <b>{html.escape(stone)}</b> mega stone added to your inventory!")
        try:
            await context.bot.send_message(referrer_id, "\n".join(lines), parse_mode=ParseMode.HTML)
        except Exception:
            pass


async def process_referral(referrer_id, referred_id, context):
    if not record_referral(referrer_id, referred_id):
        return
    count = get_referral_count(referrer_id)
    await check_referral_milestones(referrer_id, count, context)


async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = ensure_started(update)
    me = await context.bot.get_me()
    ref_link = f"https://t.me/{me.username}?start=ref_{user_id}"
    count = get_referral_count(user_id)
    lines = [
        "👥 <b>Referral Program</b>\n",
        f"Share your link and earn rewards for every new player who joins!\n",
        f"🔗 <code>{ref_link}</code>\n",
        f"Total referrals: <b>{count}</b>\n",
        "<b>Milestones:</b>",
    ]
    for threshold, rewards in REFERRAL_MILESTONES:
        given = bool(get_item_qty(user_id, f"_ref_ms_{threshold}"))
        if given:
            status = "✅"
        elif count >= threshold:
            status = "🔓"
        else:
            status = "🔒"
        reward_parts = []
        if "pd" in rewards:
            reward_parts.append(f"{rewards['pd']} PD")
        if rewards.get("non_legendary_poke"):
            reward_parts.append("Random Pokémon (186 IVs)")
        if rewards.get("legendary_poke"):
            reward_parts.append("Random Legendary (186 IVs)")
        if rewards.get("random_tm"):
            reward_parts.append("Random TM")
        if rewards.get("mega_stone"):
            reward_parts.append("Random Mega Stone")
        lines.append(f"{status} <b>{threshold} referral{'s' if threshold > 1 else ''}:</b> {', '.join(reward_parts)}")
    lines.append("\n<i>Only new users count. Each person can only be referred once.</i>")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


_active_team_slot = {}


def get_active_team_slot(user_id):
    return _active_team_slot.get(user_id, 1)


def set_active_team_slot(user_id, slot):
    _active_team_slot[user_id] = slot


def build_team_text(user_id):
    slot = get_active_team_slot(user_id)
    ids = get_team_ids(user_id)
    now = datetime.now().strftime("%I:%M %p")
    lines = [f"<b>Active Team [ TEAM {slot} ]</b>\n"]
    if ids:
        for index, caught_id in enumerate(ids, 1):
            row = get_pokemon_row(user_id, caught_id)
            if row:
                lines.append(f"{index}. {html.escape(display_name(row))} - Lv. {row['level']}  {now}")
    else:
        lines.append("No Pokémon in team. Tap <b>Add</b> to add one.")
    return "\n".join(lines)


def build_team_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Team 1", callback_data="team:slot:1"),
            InlineKeyboardButton("Team 2", callback_data="team:slot:2"),
        ],
        [
            InlineKeyboardButton("Team 3", callback_data="team:slot:3"),
            InlineKeyboardButton("Team 4", callback_data="team:slot:4"),
        ],
        [
            InlineKeyboardButton("Team 5", callback_data="team:slot:5"),
            InlineKeyboardButton("Team 6", callback_data="team:slot:6"),
        ],
        [
            InlineKeyboardButton("Add", callback_data="team:add:0"),
            InlineKeyboardButton("Remove", callback_data="team:remove"),
        ],
        [
            InlineKeyboardButton("Change Order", callback_data="team:order"),
            InlineKeyboardButton("Randomize", callback_data="team:randomize"),
        ],
    ])


def build_add_poke_text(user_id, index):
    rows = collection_rows(user_id)
    if not rows:
        return None, 0, 0
    total = len(rows)
    index = max(0, min(index, total - 1))
    row = rows[index]
    team_ids = get_team_ids(user_id)
    in_team = row["id"] in team_ids
    status = " [In Team]" if in_team else ""
    now = datetime.now().strftime("%I:%M %p")
    text = (
        f"<b>Add Pokémon to Team</b>\n\n"
        f"<b>#{index + 1} / {total}</b>\n"
        f"🔹 <b>{html.escape(display_name(row))}</b>{html.escape(status)}\n"
        f"  Lv. {row['level']}  |  IV: {iv_total(row)}/186\n"
        f"  Nature: {html.escape(row['nature'])}\n"
        f"  Caught ID: #{row['id']}  |  {now}"
    )
    return text, index, total


def build_add_poke_keyboard(user_id, index, total):
    rows = collection_rows(user_id)
    team_ids = get_team_ids(user_id)
    row = rows[index] if rows and index < len(rows) else None
    in_team = row and row["id"] in team_ids if row else False
    nav_row = []
    if index > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Back", callback_data=f"team:add:{index - 1}"))
    if not in_team and row:
        nav_row.append(InlineKeyboardButton("✅ Add", callback_data=f"team:addpoke:{row['id']}:{index}"))
    if index < total - 1:
        nav_row.append(InlineKeyboardButton("Skip ➡️", callback_data=f"team:add:{index + 1}"))
    bottom_row = [InlineKeyboardButton("⬅️ Back to Team", callback_data="team:main")]
    return InlineKeyboardMarkup([nav_row, bottom_row])


async def team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = ensure_started(update)
    text = build_team_text(user_id)
    keyboard = build_team_keyboard()
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


async def team_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = ensure_started(update)
    parts = query.data.split(":")

    if parts[1] == "main":
        text = build_team_text(user_id)
        keyboard = build_team_keyboard()
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

    elif parts[1] == "slot":
        slot = safe_int(parts[2], 1)
        set_active_team_slot(user_id, slot)
        text = build_team_text(user_id)
        keyboard = build_team_keyboard()
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

    elif parts[1] == "add":
        index = safe_int(parts[2], 0)
        text, index, total = build_add_poke_text(user_id, index)
        if text is None:
            await query.edit_message_text("No Pokémon in your collection yet. Use /hunt to catch some!")
            return
        keyboard = build_add_poke_keyboard(user_id, index, total)
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

    elif parts[1] == "addpoke":
        caught_id = safe_int(parts[2])
        index = safe_int(parts[3], 0)
        if caught_id and get_pokemon_row(user_id, caught_id):
            team_ids = get_team_ids(user_id)
            if caught_id not in team_ids:
                if len(team_ids) >= 6:
                    await query.answer("Team is full (max 6)!", show_alert=True)
                    return
                team_ids.append(caught_id)
                set_team_ids(user_id, team_ids)
                await query.answer("Added to team!")
            else:
                await query.answer("Already in team!")
        rows = collection_rows(user_id)
        total = len(rows)
        next_index = min(index + 1, total - 1)
        text, next_index, total = build_add_poke_text(user_id, next_index)
        if text is None:
            text = build_team_text(user_id)
            keyboard = build_team_keyboard()
        else:
            keyboard = build_add_poke_keyboard(user_id, next_index, total)
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

    elif parts[1] == "remove":
        team_ids = get_team_ids(user_id)
        if not team_ids:
            await query.answer("Your team is already empty.", show_alert=True)
            return
        if len(team_ids) == 1:
            set_team_ids(user_id, [])
        else:
            set_team_ids(user_id, team_ids[:-1])
        await query.answer("Last Pokémon removed from team.")
        text = build_team_text(user_id)
        keyboard = build_team_keyboard()
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

    elif parts[1] == "randomize":
        rows = collection_rows(user_id)
        if not rows:
            await query.answer("No Pokémon to randomize!", show_alert=True)
            return
        sample_size = min(6, len(rows))
        random_ids = [row["id"] for row in random.sample(rows, sample_size)]
        set_team_ids(user_id, random_ids)
        await query.answer("Team randomized!")
        text = build_team_text(user_id)
        keyboard = build_team_keyboard()
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

    elif parts[1] == "order":
        team_ids = get_team_ids(user_id)
        if len(team_ids) < 2:
            await query.answer("Need at least 2 Pokémon to change order.", show_alert=True)
            return
        team_ids = team_ids[1:] + [team_ids[0]]
        set_team_ids(user_id, team_ids)
        await query.answer("Order rotated!")
        text = build_team_text(user_id)
        keyboard = build_team_keyboard()
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


def inv_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Pokéballs", callback_data="inv:pokeballs"),
            InlineKeyboardButton("Stones", callback_data="inv:stones"),
            InlineKeyboardButton("TMs", callback_data="inv:tms"),
        ],
        [
            InlineKeyboardButton("Eggs", callback_data="inv:eggs"),
            InlineKeyboardButton("Mega Stones", callback_data="inv:mega"),
            InlineKeyboardButton("Z-Crystals", callback_data="inv:zcrystal"),
        ],
    ])


def build_inv_main_text(user_id):
    user = get_user(user_id)
    with db() as conn:
        rows = conn.execute("SELECT item_name, quantity FROM inventory WHERE user_id = ? AND quantity > 0 ORDER BY item_name", (user_id,)).fetchall()
    items_map = {r["item_name"]: r["quantity"] for r in rows}
    omni_ring = "Owned" if items_map.get("Omni Ring", 0) > 0 else "Not Owned"
    egg_incubator = "Owned" if items_map.get("Egg Incubator", 0) > 0 else "Not Owned"
    rare_candy = items_map.get("Rare Candy", 0)
    berry = items_map.get("Berry", 0)
    vitamin = items_map.get("Vitamin", 0)
    shadow_shards = items_map.get("Shadow Shard", 0)
    z_ring = "Owned" if items_map.get("Z Ring", 0) > 0 else "Not Owned"
    lines = [
        "🎒 <b>Your Inventory:</b>\n",
        f"    🧊 Omni Ring : {omni_ring}",
        f"    🥚 Egg Incubator : {egg_incubator}",
        f"    💍 Z Ring : {z_ring}\n",
        f" • PokéDollars 💰: {user['coins']}",
        f" • Shadow Shards 🔮: {shadow_shards}\n",
        "<u>Items:</u>",
        f"    🍬 Rare Candy: {rare_candy}",
        f"    🫐 Berry: {berry}",
        f"    🧴 Vitamin: {vitamin}",
    ]
    return "\n".join(lines)


def build_inv_category_text(user_id, category):
    with db() as conn:
        rows = conn.execute("SELECT item_name, quantity FROM inventory WHERE user_id = ? AND quantity > 0 ORDER BY item_name", (user_id,)).fetchall()
    items = []
    title = ""
    if category == "pokeballs":
        title = "🔴 <b>Pokéballs:</b>\n"
        for r in rows:
            if "Ball" in r["item_name"] or r["item_name"] == "Pokeball":
                items.append(f"  • {html.escape(r['item_name'])}: {r['quantity']}")
    elif category == "stones":
        title = "💎 <b>Stones:</b>\n"
        for r in rows:
            if "Stone" in r["item_name"]:
                items.append(f"  • {html.escape(r['item_name'])}: {r['quantity']}")
    elif category == "tms":
        title = "💿 <b>TMs:</b>\n"
        for r in rows:
            if r["item_name"].startswith("TM"):
                items.append(f"  • {html.escape(r['item_name'])}: {r['quantity']}")
    elif category == "eggs":
        title = "🥚 <b>Eggs:</b>\n"
        with db() as conn:
            eggs = conn.execute("SELECT * FROM eggs WHERE user_id = ? ORDER BY steps_remaining", (user_id,)).fetchall()
        if eggs:
            for egg in eggs:
                items.append(f"  • {html.escape(egg['egg_type'])} #{egg['id']}: {egg['steps_remaining']} hunts left")
        else:
            items.append("  No eggs. Find them while using /hunt.")
    elif category == "mega":
        title = "💜 <b>Mega Stones:</b>\n"
        for r in rows:
            if r["item_name"] in MEGA_STONES:
                items.append(f"  • {html.escape(r['item_name'])}: {r['quantity']} — {html.escape(MEGA_STONES[r['item_name']])}")
    elif category == "zcrystal":
        title = "💛 <b>Z-Crystals:</b>\n"
        for r in rows:
            if r["item_name"] in Z_CRYSTALS:
                items.append(f"  • {html.escape(r['item_name'])}: {r['quantity']} — {html.escape(Z_CRYSTALS[r['item_name']])}")
    if not items and category not in ("eggs",):
        items.append("  None owned.")
    return title + "\n".join(items)


async def inv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = ensure_started(update)
    text = build_inv_main_text(user_id)
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=inv_keyboard())


async def inv_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = ensure_started(update)
    category = query.data.split(":")[1]
    if category == "main":
        text = build_inv_main_text(user_id)
    else:
        text = build_inv_category_text(user_id, category)
    back_row = [InlineKeyboardButton("⬅️ Back", callback_data="inv:main")]
    if category == "main":
        keyboard = inv_keyboard()
    else:
        keyboard = InlineKeyboardMarkup([back_row])
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


SORT_LABELS = {"caught": "Caught", "name": "Name ▲", "ivs": "IVs ▼", "level": "Level ▼"}
COLLECTION_PER_PAGE = 20


def build_collection_text(user_id, page):
    rows = collection_rows(user_id)
    if not rows:
        return None, 0, 0
    total = len(rows)
    total_pages = max(1, math.ceil(total / COLLECTION_PER_PAGE))
    page = max(1, min(page, total_pages))
    subset = rows[(page - 1) * COLLECTION_PER_PAGE : page * COLLECTION_PER_PAGE]
    user = get_user(user_id)
    sort = user["collection_sort"] if user else "caught"
    sort_label = SORT_LABELS.get(sort, sort.title())
    lines = ["🎮 <b>Your Pokémons:</b>\n"]
    start_num = (page - 1) * COLLECTION_PER_PAGE + 1
    for i, row in enumerate(subset, start=start_num):
        species = html.escape(row["pokemon_name"])
        nick = row["nickname"]
        is_legendary = row["pokemon_id"] in LEGENDARY_IDS
        prefix = "🔵 " if is_legendary else ""
        if nick:
            display = f"{html.escape(nick)} ({species})"
        else:
            display = species
        ivs = iv_total(row)
        lines.append(f"{i}. {prefix}{display} - {ivs} IVs")
    lines.append(f"\nTotal: {total} | Page: {page}/{total_pages}")
    lines.append(f"Sort: {sort_label} | Display: Total IVs")
    return "\n".join(lines), page, total_pages


def build_collection_keyboard(page, total_pages):
    row1 = []
    row2 = []
    if page > 1:
        row1.append(InlineKeyboardButton("⬅️", callback_data=f"col:{page - 1}"))
    row1.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="col:noop"))
    if page < total_pages:
        row1.append(InlineKeyboardButton("➡️", callback_data=f"col:{page + 1}"))
    if page - 5 >= 1:
        row2.append(InlineKeyboardButton("⏪ 5", callback_data=f"col:{page - 5}"))
    if page - 10 >= 1:
        row2.append(InlineKeyboardButton("⏮️ 10", callback_data=f"col:{page - 10}"))
    if page + 5 <= total_pages:
        row2.append(InlineKeyboardButton("5 ⏩", callback_data=f"col:{page + 5}"))
    if page + 10 <= total_pages:
        row2.append(InlineKeyboardButton("10 ⏭️", callback_data=f"col:{page + 10}"))
    buttons = [row1]
    if row2:
        buttons.append(row2)
    return InlineKeyboardMarkup(buttons)


async def collection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = ensure_started(update)
    page = max(1, safe_int(context.args[0], 1) if context.args else 1)
    text, page, total_pages = build_collection_text(user_id, page)
    if text is None:
        await update.message.reply_text("No Pokémon yet. Use /hunt.")
        return
    keyboard = build_collection_keyboard(page, total_pages)
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


async def collection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "col:noop":
        return
    user_id = ensure_started(update)
    page = safe_int(query.data.split(":")[1], 1)
    text, page, total_pages = build_collection_text(user_id, page)
    if text is None:
        await query.edit_message_text("No Pokémon yet. Use /hunt.")
        return
    keyboard = build_collection_keyboard(page, total_pages)
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


def slot_keyboard(current_sort):
    labels = {"caught": "🕐 Caught", "name": "🔤 Name", "ivs": "💎 IVs", "level": "⬆️ Level"}
    row = []
    for key, label in labels.items():
        display = f"✅ {label}" if key == current_sort else label
        row.append(InlineKeyboardButton(display, callback_data=f"slot:{key}"))
    return InlineKeyboardMarkup([row])


async def slot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = ensure_started(update)
    user = get_user(user_id)
    current_sort = user["collection_sort"] if user else "caught"
    if context.args:
        choice = context.args[0].lower()
        if choice in ["name", "caught", "ivs", "level"]:
            update_user(user_id, collection_sort=choice)
            current_sort = choice
    text = (
        "<b>Collection Sort</b>\n"
        f"Current: <b>{html.escape(current_sort)}</b>\n\n"
        "Choose how to sort your Pokémon collection:"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=slot_keyboard(current_sort))


async def slot_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = ensure_started(update)
    choice = query.data.split(":")[1]
    if choice not in ["name", "caught", "ivs", "level"]:
        return
    update_user(user_id, collection_sort=choice)
    text = (
        "<b>Collection Sort</b>\n"
        f"Current: <b>{html.escape(choice)}</b>\n\n"
        "Choose how to sort your Pokémon collection:"
    )
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=slot_keyboard(choice))


async def create_card_image(row):
    info = poke_data.get_base_stats_types_sprites(row["pokemon_id"])
    base_stats = info["stats"]
    card_evs = get_evs(row)
    actual = poke_data.calculate_stats(base_stats, row["level"], row_ivs(row), row["nature"], card_evs)
    width, height = 900, 560
    img = Image.new("RGB", (width, height), (20, 24, 35))
    draw = ImageDraw.Draw(img)
    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 46)
        font = ImageFont.truetype("DejaVuSans.ttf", 25)
        small = ImageFont.truetype("DejaVuSans.ttf", 20)
    except Exception:
        title_font = font = small = None
    for y in range(height):
        shade = int(30 + y * 0.08)
        draw.line([(0, y), (width, y)], fill=(shade, 28, 55 + int(y * 0.04)))
    draw.rounded_rectangle((24, 24, width - 24, height - 24), radius=30, outline=(255, 212, 85), width=4)
    art = load_pokemon_art(info, (285, 285))
    if art:
        img.paste(art, (52 + (285 - art.width) // 2, 122 + (285 - art.height) // 2), art)
    name = display_name(row)
    draw.text((330, 52), f"{name}  #{row['id']}", fill=(255, 236, 160), font=title_font)
    draw.text((333, 108), f"{info['name']} | Lv.{row['level']} | {', '.join(info['types']).title()}", fill=(230, 235, 255), font=font)
    draw.text((333, 146), f"Nature: {row['nature']} | IV Total: {iv_total(row)}/186", fill=(190, 220, 255), font=font)
    left = 333
    y = 205
    labels = [("HP", "hp"), ("Atk", "attack"), ("Def", "defense"), ("SpA", "special-attack"), ("SpD", "special-defense"), ("Spe", "speed")]
    ivs = row_ivs(row)
    for label, key in labels:
        draw.text((left, y), f"{label}: {actual[key]:3d}  IV {ivs[key]:2d}", fill=(245, 245, 245), font=small)
        bar_w = min(230, actual[key] * 2)
        draw.rounded_rectangle((left + 180, y + 5, left + 180 + bar_w, y + 20), radius=6, fill=(98, 191, 255))
        y += 42
    moves = json.loads(row["moves_learned"])
    draw.text((52, 410), "Moves: " + ", ".join(m.replace("-", " ").title() for m in moves), fill=(255, 255, 255), font=small)

    # Also show move details (stats move in level section)
    move_y = 440
    for m_name in moves[:4]:
        try:
            m = poke_data.get_move_details(m_name)
            draw.text((52, move_y), f"{m_name.replace('-',' ').title()}: Pwr {m['power']} Acc {m['accuracy']} [{m['type'].title()}]", fill=(190, 215, 245), font=small)
            move_y += 24
        except Exception:
            pass

    draw.text((52, move_y + 4), f"Caught: {row['caught_at']}", fill=(190, 195, 215), font=small)
    output = BytesIO()
    img.save(output, format="PNG")
    output.seek(0)
    return output


async def card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = ensure_started(update)
    row = None
    caught_id = None
    if context.args:
        query = " ".join(context.args)
        caught_id = safe_int(query)
        if caught_id:
            row = get_pokemon_row(user_id, caught_id)
            if not row:
                await update.message.reply_text(f"No Pokémon with ID #{caught_id} in your collection.")
                return
        else:
            matches = find_all_owned_pokemon(user_id, query)
            if not matches:
                await update.message.reply_text(f"You do not own a Pokémon named '{query}'. Use /collection to see your owned Pokémon names.")
                return
            if len(matches) > 1:
                buttons = []
                for m in matches:
                    label = m["pokemon_name"]
                    if m["nickname"]:
                        label = f"{m['nickname']} ({m['pokemon_name']})"
                    label += f" Lv.{m['level']} #{m['id']}"
                    buttons.append([InlineKeyboardButton(label, callback_data=f"card_pick:{m['id']}")])
                keyboard = InlineKeyboardMarkup(buttons)
                await update.message.reply_text(
                    f"You have <b>{len(matches)}</b> Pokémon named <b>{html.escape(query.title())}</b>. Which one do you want to view?",
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard,
                )
                return
            row = matches[0]
            caught_id = row["id"]
    else:
        await update.message.reply_text("Use: /card <owned Pokémon name>. Example: /card Pikachu")
        return
    row = row or get_pokemon_row(user_id, caught_id)
    if not row:
        await update.message.reply_text("That Pokémon is not in your collection. /card only shows Pokémon you own.")
        return
    image = await create_card_image(row)
    await update.message.reply_photo(
        InputFile(image, filename=f"card_{caught_id}.png"),
        caption=caught_card_caption(row),
        parse_mode=ParseMode.HTML,
        reply_markup=caught_card_keyboard(caught_id),
    )


async def cardview_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = ensure_started(update)
    _, tab, caught_id_text = query.data.split(":")
    caught_id = safe_int(caught_id_text)
    row = get_pokemon_row(user_id, caught_id)
    if not row:
        await query.edit_message_caption(caption="This Pokémon is not in your collection anymore.", parse_mode=ParseMode.HTML)
        return
    await query.edit_message_caption(caption=caught_card_caption(row, tab), parse_mode=ParseMode.HTML, reply_markup=caught_card_keyboard(caught_id))


async def card_pick_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = ensure_started(update)
    caught_id = safe_int(query.data.split(":")[1])
    row = get_pokemon_row(user_id, caught_id)
    if not row:
        await query.edit_message_text("That Pokémon is not in your collection anymore.")
        return
    image = await create_card_image(row)
    await query.message.reply_photo(
        InputFile(image, filename=f"card_{caught_id}.png"),
        caption=caught_card_caption(row),
        parse_mode=ParseMode.HTML,
        reply_markup=caught_card_keyboard(caught_id),
    )
    await query.edit_message_reply_markup(reply_markup=None)


async def data_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_started(update)
    ident = context.args[0] if context.args else "ditto"
    try:
        info = poke_data.get_base_stats_types_sprites(ident)
        data = poke_data.get_pokemon(ident)
        abilities = [a["ability"]["name"].replace("-", " ").title() for a in data.get("abilities", [])]
        moves = [m["move"]["name"].replace("-", " ").title() for m in data.get("moves", [])[:12]]
        lines = [
            f"<b>{html.escape(info['name'])}</b> #{info['id']}",
            f"Types: {', '.join(info['types']).title()}",
            f"Abilities: {', '.join(abilities)}",
            "Base Stats:",
        ]
        for key, value in info["stats"].items():
            lines.append(f"• {key.title()}: {value}")
        lines.append("Moves: " + ", ".join(moves))
        if info["sprite"]:
            await update.message.reply_photo(info["sprite"], caption="\n".join(lines), parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)
    except Exception as exc:
        await update.message.reply_text(f"Could not fetch PokéAPI data: {exc}")


# ─── UPDATED BATTLE SYSTEM ─────────────────────────────────────────────────────

async def battle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Group-only battle command. Must reply to target player.
    Requires /team set first.
    """
    user_id = ensure_started(update)
    chat = update.effective_chat

    # Group only
    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text(
            "⚔️ <b>/battle</b> only works in group chats!\n"
            "Reply to another player's message in a group to challenge them.",
            parse_mode=ParseMode.HTML,
        )
        return

    # Must reply to someone
    reply = update.message.reply_to_message
    if not reply or not reply.from_user or reply.from_user.is_bot:
        await update.message.reply_text(
            "⚔️ To start a battle, <b>reply</b> to another player's message and use /battle!\n"
            "Example: Reply to someone's message → /battle",
            parse_mode=ParseMode.HTML,
        )
        return

    challenger_id = user_id
    opponent_id = reply.from_user.id

    if challenger_id == opponent_id:
        await update.message.reply_text("You cannot battle yourself!", parse_mode=ParseMode.HTML)
        return

    # Check teams
    challenger_team = get_team_ids(challenger_id)
    if not challenger_team:
        await update.message.reply_text(
            "❌ You need to set a team first!\nUse /team to add Pokémon to your team.",
            parse_mode=ParseMode.HTML,
        )
        return

    add_user(opponent_id, reply.from_user.full_name or reply.from_user.first_name or str(opponent_id))
    opponent_team = get_team_ids(opponent_id)
    if not opponent_team:
        target_name = reply.from_user.full_name or reply.from_user.first_name or str(opponent_id)
        await update.message.reply_text(
            f"❌ <b>{html.escape(target_name)}</b> hasn't set a team yet!\n"
            f"They need to use /team first.",
            parse_mode=ParseMode.HTML,
        )
        return

    # Get pokemon info for challenge image
    challenger_poke_row = get_pokemon_row(challenger_id, challenger_team[0])
    opponent_poke_row = get_pokemon_row(opponent_id, opponent_team[0])

    if not challenger_poke_row or not opponent_poke_row:
        await update.message.reply_text("Could not load team Pokémon. Try resetting your team with /team.", parse_mode=ParseMode.HTML)
        return

    challenger_poke_info = poke_data.get_base_stats_types_sprites(challenger_poke_row["pokemon_id"])
    opponent_poke_info = poke_data.get_base_stats_types_sprites(opponent_poke_row["pokemon_id"])

    challenger_user = update.effective_user
    opponent_user = reply.from_user

    challenger_name = challenger_user.full_name or challenger_user.first_name or str(challenger_id)
    opponent_name = opponent_user.full_name or opponent_user.first_name or str(opponent_id)

    # Create challenge image
    try:
        challenge_img = create_challenge_image(
            challenger_id, challenger_name,
            opponent_id, opponent_name,
            challenger_poke_info, opponent_poke_info
        )
    except Exception:
        challenge_img = None

    # Insert challenge record
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO battle_challenges (challenger_id, opponent_id, chat_id, status, created_at) VALUES (?, ?, ?, 'pending', ?)",
            (challenger_id, opponent_id, chat.id, int(time.time()))
        )
        challenge_id = cur.lastrowid

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Accept", callback_data=f"challenge:{challenge_id}:accept"),
            InlineKeyboardButton("❌ Decline", callback_data=f"challenge:{challenge_id}:decline"),
        ]
    ])

    caption = (
        f"⚔️ <b>Battle Challenge!</b>\n\n"
        f"<b>{html.escape(challenger_name)}</b> challenges <b>{html.escape(opponent_name)}</b>!\n\n"
        f"🔵 {html.escape(challenger_name)}: {html.escape(challenger_poke_info['name'])} Lv.{challenger_poke_row['level']}\n"
        f"🔴 {html.escape(opponent_name)}: {html.escape(opponent_poke_info['name'])} Lv.{opponent_poke_row['level']}\n\n"
        f"{html.escape(opponent_name)}, do you accept the challenge?"
    )

    if challenge_img:
        msg = await update.message.reply_photo(
            InputFile(challenge_img, filename="challenge.png"),
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
        )
    else:
        msg = await update.message.reply_text(caption, parse_mode=ParseMode.HTML, reply_markup=keyboard)

    # Update challenge with message id
    with db() as conn:
        conn.execute("UPDATE battle_challenges SET message_id = ? WHERE id = ?", (msg.message_id, challenge_id))


async def challenge_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Accept/Decline for battle challenge."""
    query = update.callback_query
    await query.answer()
    user_id = ensure_started(update)

    parts = query.data.split(":")
    challenge_id = safe_int(parts[1])
    action = parts[2]

    with db() as conn:
        challenge = conn.execute("SELECT * FROM battle_challenges WHERE id = ?", (challenge_id,)).fetchone()

    if not challenge:
        await query.answer("Challenge not found or expired.", show_alert=True)
        return

    if challenge["status"] != "pending":
        await query.answer("This challenge has already been resolved.", show_alert=True)
        return

    # Only the challenged player can respond
    if user_id != challenge["opponent_id"]:
        await query.answer("Only the challenged player can accept or decline!", show_alert=True)
        return

    if action == "decline":
        with db() as conn:
            conn.execute("UPDATE battle_challenges SET status = 'declined' WHERE id = ?", (challenge_id,))
        try:
            await query.edit_message_caption(
                caption="❌ Battle challenge declined.",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            await query.edit_message_text("❌ Battle challenge declined.", parse_mode=ParseMode.HTML)
        return

    # Accept: start the battle
    challenger_id = challenge["challenger_id"]
    opponent_id = challenge["opponent_id"]

    challenger_team = get_team_ids(challenger_id)
    opponent_team = get_team_ids(opponent_id)

    if not challenger_team or not opponent_team:
        await query.answer("One of the players no longer has a valid team.", show_alert=True)
        return

    challenger_row = get_pokemon_row(challenger_id, challenger_team[0])
    opponent_row = get_pokemon_row(opponent_id, opponent_team[0])

    if not challenger_row or not opponent_row:
        await query.answer("Could not load Pokémon data.", show_alert=True)
        return

    challenger_info = poke_data.get_base_stats_types_sprites(challenger_row["pokemon_id"])
    opponent_info = poke_data.get_base_stats_types_sprites(opponent_row["pokemon_id"])

    challenger_ivs = row_ivs(challenger_row)
    opponent_ivs = row_ivs(opponent_row)
    challenger_evs = get_evs(challenger_row)
    opponent_evs = get_evs(opponent_row)
    challenger_stats = poke_data.calculate_stats(challenger_info["stats"], challenger_row["level"], challenger_ivs, challenger_row["nature"], challenger_evs)
    opponent_stats = poke_data.calculate_stats(opponent_info["stats"], opponent_row["level"], opponent_ivs, opponent_row["nature"], opponent_evs)

    battle_id = f"pvp_{challenge_id}_{int(time.time())}"

    with db() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO pvp_battles
            (battle_id, challenger_id, opponent_id, challenger_poke_id, opponent_poke_id,
             challenger_hp, opponent_hp, current_turn, challenger_team, opponent_team,
             challenger_team_idx, opponent_team_idx,
             challenger_mega_used, challenger_z_used, opponent_mega_used, opponent_z_used,
             challenger_transformed, opponent_transformed,
             chat_id, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, 0, 0, 0, 0, 0, 0, 0, 0, ?, 'active', ?)""",
            (
                battle_id, challenger_id, opponent_id,
                challenger_row["id"], opponent_row["id"],
                challenger_stats["hp"], opponent_stats["hp"],
                json.dumps(challenger_team), json.dumps(opponent_team),
                challenge["chat_id"], int(time.time())
            )
        )
        conn.execute("UPDATE battle_challenges SET status = 'accepted' WHERE id = ?", (challenge_id,))

    # Build battle image & message
    challenger_user_obj = await context.bot.get_chat(challenger_id)
    challenger_name = challenger_user_obj.full_name or challenger_user_obj.first_name or str(challenger_id)
    opponent_user_obj = update.effective_user
    opponent_name = opponent_user_obj.full_name or opponent_user_obj.first_name or str(opponent_id)

    battle_img = create_pvp_battle_image(
        challenger_info, opponent_info,
        challenger_stats["hp"], challenger_stats["hp"],
        opponent_stats["hp"], opponent_stats["hp"],
        challenger_row["level"], opponent_row["level"],
        challenger_name, opponent_name
    )

    # Get mega/z info for challenger's turn
    challenger_mega = get_player_mega_stone(challenger_id, challenger_info["name"])
    challenger_z = get_player_z_crystal(challenger_id, challenger_info["types"])

    battle_obj = get_pvp_battle(battle_id)

    caption = build_battle_move_text(
        battle_obj, challenger_row, challenger_info,
        opponent_row, opponent_info, True, challenger_name
    )

    keyboard = build_pvp_move_keyboard(
        battle_id, challenger_row, True,
        mega_stone=challenger_mega,
        z_crystal=challenger_z,
        mega_used=False, z_used=False,
        my_team_size=len(challenger_team),
        my_team_idx=0
    )

    try:
        await query.edit_message_caption(caption="⚔️ Battle accepted! Starting battle...", parse_mode=ParseMode.HTML)
    except Exception:
        pass

    battle_msg = await query.message.reply_photo(
        InputFile(battle_img, filename="battle.png"),
        caption=f"⚔️ <b>Battle Started!</b>\n{html.escape(challenger_name)} vs {html.escape(opponent_name)}\n\n{caption}\n\n<b>{html.escape(challenger_name)}'s turn!</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard,
    )

    with db() as conn:
        conn.execute("UPDATE pvp_battles SET message_id = ? WHERE battle_id = ?", (battle_msg.message_id, battle_id))


async def pvp_battle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all PvP battle actions."""
    query = update.callback_query
    await query.answer()
    user_id = ensure_started(update)

    parts = query.data.split(":")
    # Format: pvp:{battle_id}:{role}:{action}[:{extra}]
    battle_id = parts[1]
    role = parts[2]  # 'c' = challenger, 'o' = opponent
    action = parts[3]
    extra = parts[4] if len(parts) > 4 else None

    battle = get_pvp_battle(battle_id)
    if not battle:
        await query.answer("Battle not found or already ended.", show_alert=True)
        return

    if battle["status"] != "active":
        await query.answer("This battle is already over.", show_alert=True)
        return

    is_challenger = (role == "c")
    expected_user = battle["challenger_id"] if is_challenger else battle["opponent_id"]

    if user_id != expected_user:
        await query.answer("It's not your turn or you're not in this battle!", show_alert=True)
        return

    # Determine whose turn it is (0 = challenger, 1 = opponent)
    current_turn = battle["current_turn"]
    if is_challenger and current_turn != 0:
        await query.answer("It's not your turn yet! Wait for the opponent.", show_alert=True)
        return
    if not is_challenger and current_turn != 1:
        await query.answer("It's not your turn yet! Wait for the challenger.", show_alert=True)
        return

    challenger_id = battle["challenger_id"]
    opponent_id = battle["opponent_id"]

    my_poke_id = battle["challenger_poke_id"] if is_challenger else battle["opponent_poke_id"]
    opp_poke_id = battle["opponent_poke_id"] if is_challenger else battle["challenger_poke_id"]

    my_row = get_pokemon_row(challenger_id if is_challenger else opponent_id, my_poke_id)
    opp_row = get_pokemon_row(opponent_id if is_challenger else challenger_id, opp_poke_id)

    if not my_row or not opp_row:
        await query.answer("Could not load Pokémon data.", show_alert=True)
        return

    my_info = poke_data.get_base_stats_types_sprites(my_row["pokemon_id"])
    opp_info = poke_data.get_base_stats_types_sprites(opp_row["pokemon_id"])

    my_evs_dict = get_evs(my_row)
    opp_evs_dict = get_evs(opp_row)
    my_stats = poke_data.calculate_stats(my_info["stats"], my_row["level"], row_ivs(my_row), my_row["nature"], my_evs_dict)
    opp_stats = poke_data.calculate_stats(opp_info["stats"], opp_row["level"], row_ivs(opp_row), opp_row["nature"], opp_evs_dict)

    my_hp = battle["challenger_hp"] if is_challenger else battle["opponent_hp"]
    opp_hp = battle["opponent_hp"] if is_challenger else battle["challenger_hp"]
    my_max_hp = my_stats["hp"]
    opp_max_hp = opp_stats["hp"]

    my_mega_used = battle["challenger_mega_used"] if is_challenger else battle["opponent_mega_used"]
    my_z_used = battle["challenger_z_used"] if is_challenger else battle["opponent_z_used"]
    my_transformed = battle["challenger_transformed"] if is_challenger else battle["opponent_transformed"]

    # Get player names
    try:
        challenger_obj = await context.bot.get_chat(challenger_id)
        challenger_name = challenger_obj.full_name or str(challenger_id)
    except Exception:
        challenger_name = str(challenger_id)
    try:
        opponent_obj = await context.bot.get_chat(opponent_id)
        opponent_name = opponent_obj.full_name or str(opponent_id)
    except Exception:
        opponent_name = str(opponent_id)

    my_name = challenger_name if is_challenger else opponent_name
    opp_name = opponent_name if is_challenger else challenger_name

    log_lines = []

    if action == "forfeit":
        # Current player forfeits
        winner_id = opponent_id if is_challenger else challenger_id
        loser_id = user_id
        winner_name = opp_name
        update_pvp_battle(battle_id, status="ended")

        winner_user = get_user(winner_id)
        loser_user = get_user(loser_id)
        update_user(winner_id, coins=winner_user["coins"] + 200, wins=(winner_user["wins"] or 0) + 1)
        update_user(loser_id, losses=(loser_user["losses"] or 0) + 1)

        winner_team = json.loads(battle["challenger_team"] if not is_challenger else battle["opponent_team"])
        winner_poke_row = get_pokemon_row(winner_id, winner_team[0])
        winner_info = poke_data.get_base_stats_types_sprites(winner_poke_row["pokemon_id"])
        winner_poke_stats = poke_data.calculate_stats(winner_info["stats"], winner_poke_row["level"], row_ivs(winner_poke_row), winner_poke_row["nature"], get_evs(winner_poke_row))
        win_hp = battle["opponent_hp"] if is_challenger else battle["challenger_hp"]

        win_img = create_win_image(winner_name, winner_id, winner_team, winner_info, win_hp, winner_poke_stats["hp"])

        await query.message.reply_photo(
            InputFile(win_img, filename="winner.png"),
            caption=f"🏆 <b>{html.escape(my_name)}</b> forfeited!\n"
                    f"<b>{html.escape(winner_name)}</b> wins and gets <b>200 PD</b>!",
            parse_mode=ParseMode.HTML,
        )
        try:
            await query.edit_message_caption(caption=f"Battle ended — {html.escape(my_name)} forfeited.", parse_mode=ParseMode.HTML)
        except Exception:
            pass
        return

    if action == "draw":
        update_pvp_battle(battle_id, status="ended")
        try:
            await query.edit_message_caption(caption=f"🤝 <b>{html.escape(my_name)}</b> offered a draw. Battle ended as draw!", parse_mode=ParseMode.HTML)
        except Exception:
            pass
        await query.message.reply_text(f"🤝 Battle between {html.escape(challenger_name)} and {html.escape(opponent_name)} ended in a draw!", parse_mode=ParseMode.HTML)
        return

    if action == "switch":
        # Show team switch options
        my_team = json.loads(battle["challenger_team"] if is_challenger else battle["opponent_team"])
        my_team_idx = battle["challenger_team_idx"] if is_challenger else battle["opponent_team_idx"]

        if len(my_team) <= 1:
            await query.answer("No other Pokémon to switch to!", show_alert=True)
            return

        switch_buttons = []
        for i, poke_id in enumerate(my_team):
            if i == my_team_idx:
                continue
            try:
                pr = get_pokemon_row(challenger_id if is_challenger else opponent_id, poke_id)
                if pr:
                    pi = poke_data.get_base_stats_types_sprites(pr["pokemon_id"])
                    ps = poke_data.calculate_stats(pi["stats"], pr["level"], row_ivs(pr), pr["nature"], get_evs(pr))
                    btn_label = f"{pi['name']} Lv.{pr['level']}"
                    switch_buttons.append([InlineKeyboardButton(btn_label, callback_data=f"pvp:{battle_id}:{role}:doswitch:{i}")])
            except Exception:
                pass

        switch_buttons.append([InlineKeyboardButton("Back", callback_data=f"pvp:{battle_id}:{role}:backswitch")])
        switch_keyboard = InlineKeyboardMarkup(switch_buttons)

        try:
            await query.edit_message_reply_markup(reply_markup=switch_keyboard)
        except Exception:
            pass
        return

    if action == "backswitch":
        # Return to normal battle keyboard
        my_mega = get_player_mega_stone(challenger_id if is_challenger else opponent_id, my_info["name"])
        my_z = get_player_z_crystal(challenger_id if is_challenger else opponent_id, my_info["types"])
        my_team = json.loads(battle["challenger_team"] if is_challenger else battle["opponent_team"])

        kb = build_pvp_move_keyboard(
            battle_id, my_row, is_challenger,
            mega_stone=my_mega if not my_mega_used else None,
            z_crystal=my_z if not my_z_used else None,
            mega_used=my_mega_used, z_used=my_z_used,
            my_team_size=len(my_team),
        )
        try:
            await query.edit_message_reply_markup(reply_markup=kb)
        except Exception:
            pass
        return

    if action == "doswitch":
        # Perform actual switch
        switch_idx = safe_int(extra, 0)
        my_team = json.loads(battle["challenger_team"] if is_challenger else battle["opponent_team"])

        if switch_idx >= len(my_team):
            await query.answer("Invalid switch target.", show_alert=True)
            return

        new_poke_id = my_team[switch_idx]
        new_poke_row = get_pokemon_row(challenger_id if is_challenger else opponent_id, new_poke_id)
        if not new_poke_row:
            await query.answer("Could not load that Pokémon.", show_alert=True)
            return

        new_poke_info = poke_data.get_base_stats_types_sprites(new_poke_row["pokemon_id"])
        new_poke_evs = get_evs(new_poke_row)
        new_poke_stats = poke_data.calculate_stats(new_poke_info["stats"], new_poke_row["level"], row_ivs(new_poke_row), new_poke_row["nature"], new_poke_evs)

        if is_challenger:
            update_pvp_battle(battle_id,
                challenger_poke_id=new_poke_id,
                challenger_hp=new_poke_stats["hp"],
                challenger_team_idx=switch_idx,
                challenger_transformed=0,
                current_turn=1  # switch turn to opponent
            )
        else:
            update_pvp_battle(battle_id,
                opponent_poke_id=new_poke_id,
                opponent_hp=new_poke_stats["hp"],
                opponent_team_idx=switch_idx,
                opponent_transformed=0,
                current_turn=0  # switch turn to challenger
            )

        battle = get_pvp_battle(battle_id)

        # Reload info
        c_row = get_pokemon_row(challenger_id, battle["challenger_poke_id"])
        o_row = get_pokemon_row(opponent_id, battle["opponent_poke_id"])
        c_info = poke_data.get_base_stats_types_sprites(c_row["pokemon_id"])
        o_info = poke_data.get_base_stats_types_sprites(o_row["pokemon_id"])
        c_stats = poke_data.calculate_stats(c_info["stats"], c_row["level"], row_ivs(c_row), c_row["nature"], get_evs(c_row))
        o_stats = poke_data.calculate_stats(o_info["stats"], o_row["level"], row_ivs(o_row), o_row["nature"], get_evs(o_row))

        battle_img = create_pvp_battle_image(
            c_info, o_info,
            battle["challenger_hp"], c_stats["hp"],
            battle["opponent_hp"], o_stats["hp"],
            c_row["level"], o_row["level"],
            challenger_name, opponent_name,
            challenger_transformed=battle["challenger_transformed"],
            opponent_transformed=battle["opponent_transformed"],
        )

        switched_name = new_poke_info["name"]
        next_turn_name = opponent_name if is_challenger else challenger_name
        next_role = "o" if is_challenger else "c"
        next_row = o_row if is_challenger else c_row
        next_info = o_info if is_challenger else c_info
        next_is_challenger = not is_challenger

        next_mega = get_player_mega_stone(opponent_id if is_challenger else challenger_id, next_info["name"])
        next_z = get_player_z_crystal(opponent_id if is_challenger else challenger_id, next_info["types"])
        next_mega_used = battle["opponent_mega_used"] if is_challenger else battle["challenger_mega_used"]
        next_z_used = battle["opponent_z_used"] if is_challenger else battle["challenger_z_used"]
        next_team = json.loads(battle["opponent_team"] if is_challenger else battle["challenger_team"])

        next_caption = build_battle_move_text(
            battle, next_row, next_info, new_poke_row, new_poke_info,
            next_is_challenger, next_turn_name
        )

        next_kb = build_pvp_move_keyboard(
            battle_id, next_row, next_is_challenger,
            mega_stone=next_mega if not next_mega_used else None,
            z_crystal=next_z if not next_z_used else None,
            mega_used=next_mega_used, z_used=next_z_used,
            my_team_size=len(next_team),
        )

        full_caption = (
            f"🔄 Switched from {html.escape(display_name(my_row))} to {html.escape(switched_name)}!\n\n"
            f"{next_caption}\n\n"
            f"<b>{html.escape(next_turn_name)}'s turn!</b>"
        )

        try:
            await query.edit_message_media(
                media=InputMediaPhoto(image_output(battle_img, "switch.png"), caption=full_caption, parse_mode=ParseMode.HTML),
                reply_markup=next_kb,
            )
        except Exception:
            try:
                await query.edit_message_caption(caption=full_caption, parse_mode=ParseMode.HTML, reply_markup=next_kb)
            except Exception:
                await query.message.reply_text(full_caption, parse_mode=ParseMode.HTML, reply_markup=next_kb)
        return

    if action == "mega":
        if my_mega_used:
            await query.answer("You already used your Mega Evolution this battle!", show_alert=True)
            return

        mega_stone = get_player_mega_stone(challenger_id if is_challenger else opponent_id, my_info["name"])
        if not mega_stone:
            await query.answer("No Mega Stone available for your current Pokémon!", show_alert=True)
            return

        # Apply Mega Evolution stat boost
        mega_poke_name = my_info["name"]
        mega_data = MEGA_EVOLUTIONS.get(mega_poke_name)
        if mega_data:
            mega_form_name, stat_boosts = mega_data
            # Try to load mega form info
            try:
                mega_info = poke_data.get_base_stats_types_sprites(mega_form_name)
                mega_stats = poke_data.calculate_stats(mega_info["stats"], my_row["level"], row_ivs(my_row), my_row["nature"], get_evs(my_row))
                # HP boost if applicable
                new_hp = min(my_hp + (mega_stats["hp"] - my_stats["hp"]), mega_stats["hp"])
            except Exception:
                mega_info = my_info
                mega_stats = my_stats
                new_hp = my_hp

        if is_challenger:
            update_pvp_battle(battle_id, challenger_mega_used=1, challenger_transformed=1, challenger_hp=new_hp)
        else:
            update_pvp_battle(battle_id, opponent_mega_used=1, opponent_transformed=1, opponent_hp=new_hp)

        battle = get_pvp_battle(battle_id)

        # Show mega transformation image
        try:
            m_art = load_pokemon_art(mega_info, (400, 400))
            if m_art:
                img = Image.new("RGB", (600, 500), (20, 10, 35))
                draw = ImageDraw.Draw(img)
                draw_gradient(draw, 600, 500, top=(15, 8, 45), bottom=(60, 20, 90))
                img.paste(m_art, ((600 - m_art.width) // 2, (450 - m_art.height) // 2), m_art)
                f = fonts()
                draw.text((50, 10), f"{mega_poke_name} changed form into {mega_info['name']}!", fill=(255, 200, 50), font=f["body"])
                mega_img = BytesIO()
                img.save(mega_img, format="PNG")
                mega_img.seek(0)
                await query.message.reply_photo(
                    InputFile(mega_img, filename="mega.png"),
                    caption=f"✨ <b>{html.escape(mega_poke_name)}</b> Mega Evolved into <b>{html.escape(mega_info['name'])}</b>!",
                    parse_mode=ParseMode.HTML,
                )
        except Exception:
            await query.message.reply_text(f"✨ <b>{html.escape(mega_poke_name)}</b> Mega Evolved!", parse_mode=ParseMode.HTML)

        # Now show updated battle with mega stats available - player still uses their move
        # Reload state and show updated keyboard
        my_mega_used = True
        my_mega = None  # Used up

        c_row = get_pokemon_row(challenger_id, battle["challenger_poke_id"])
        o_row = get_pokemon_row(opponent_id, battle["opponent_poke_id"])
        c_info_r = poke_data.get_base_stats_types_sprites(c_row["pokemon_id"])
        o_info_r = poke_data.get_base_stats_types_sprites(o_row["pokemon_id"])
        c_stats_r = poke_data.calculate_stats(c_info_r["stats"], c_row["level"], row_ivs(c_row), c_row["nature"], get_evs(c_row))
        o_stats_r = poke_data.calculate_stats(o_info_r["stats"], o_row["level"], row_ivs(o_row), o_row["nature"], get_evs(o_row))

        battle_img = create_pvp_battle_image(
            c_info_r, o_info_r,
            battle["challenger_hp"], c_stats_r["hp"],
            battle["opponent_hp"], o_stats_r["hp"],
            c_row["level"], o_row["level"],
            challenger_name, opponent_name,
            challenger_transformed=battle["challenger_transformed"],
            opponent_transformed=battle["opponent_transformed"],
        )

        cur_row = c_row if is_challenger else o_row
        my_z = get_player_z_crystal(challenger_id if is_challenger else opponent_id, my_info["types"])
        my_z_used_now = battle["challenger_z_used"] if is_challenger else battle["opponent_z_used"]
        my_team = json.loads(battle["challenger_team"] if is_challenger else battle["opponent_team"])

        cur_caption = build_battle_move_text(
            battle, cur_row, my_info, o_row if is_challenger else c_row, o_info_r if is_challenger else c_info_r,
            is_challenger, my_name
        )

        kb = build_pvp_move_keyboard(
            battle_id, cur_row, is_challenger,
            mega_stone=None,  # already used
            z_crystal=my_z if not my_z_used_now else None,
            mega_used=True, z_used=my_z_used_now,
            my_team_size=len(my_team),
        )

        mega_full_caption = f"⚡ Mega Evolved! Now choose your move:\n\n{cur_caption}\n\n<b>{html.escape(my_name)}'s turn!</b>"
        try:
            await query.edit_message_media(
                media=InputMediaPhoto(image_output(battle_img, "mega_battle.png"),
                                      caption=mega_full_caption,
                                      parse_mode=ParseMode.HTML),
                reply_markup=kb,
            )
        except Exception:
            try:
                await query.edit_message_caption(caption=mega_full_caption, parse_mode=ParseMode.HTML, reply_markup=kb)
            except Exception:
                await query.message.reply_text(mega_full_caption, parse_mode=ParseMode.HTML, reply_markup=kb)
        return

    if action == "zmove":
        if my_z_used:
            await query.answer("You already used your Z-Move this battle!", show_alert=True)
            return

        z_crystal = get_player_z_crystal(challenger_id if is_challenger else opponent_id, my_info["types"])
        if not z_crystal:
            await query.answer("No Z-Crystal available for your current Pokémon's type!", show_alert=True)
            return

        if get_item_qty(challenger_id if is_challenger else opponent_id, "Z Ring") <= 0:
            await query.answer("You need a Z Ring to use Z-Moves!", show_alert=True)
            return

        z_type = Z_CRYSTAL_TYPE[z_crystal]
        z_move_name = Z_MOVE_NAMES.get(z_type, "Z-Move")

        # Find a matching type move to boost
        moves = json.loads(my_row["moves_learned"])[:4]
        z_move = None
        for m_name in moves:
            try:
                m = poke_data.get_move_details(m_name)
                if m["type"] == z_type and m["category"] != "status":
                    z_move = m
                    z_move = dict(z_move)
                    z_move["power"] = max(m["power"] * 2, 180)
                    z_move["name"] = z_move_name
                    break
            except Exception:
                pass

        if not z_move:
            # Use a default high-power Z-move
            z_move = {"power": 175, "type": z_type, "category": "special", "accuracy": 100, "name": z_move_name, "pp": 1}

        # Calculate Z-Move damage
        damage, multi, is_crit = simple_damage(
            my_row["level"], my_stats, opp_stats, z_move, opp_info["types"],
            attacker_ability=my_info["abilities"][0] if my_info["abilities"] else None,
            attacker_types=my_info["types"]
        )

        new_opp_hp = max(0, opp_hp - damage)

        if is_challenger:
            update_pvp_battle(battle_id, challenger_z_used=1, opponent_hp=new_opp_hp, current_turn=1)
        else:
            update_pvp_battle(battle_id, opponent_z_used=1, challenger_hp=new_opp_hp, current_turn=0)

        crit_text = "\n🎯 A critical hit! 💥" if is_crit else ""
        await query.message.reply_text(
            f"⚡ <b>{html.escape(my_name)}</b> used <b>{html.escape(z_move_name)}</b>!\n"
            f"Dealt <b>{damage}</b> damage!{crit_text}",
            parse_mode=ParseMode.HTML,
        )

        battle = get_pvp_battle(battle_id)

        # Check if opponent fainted
        if new_opp_hp <= 0:
            await _handle_pvp_win(query, context, battle, battle_id, is_challenger,
                                   challenger_id, opponent_id, challenger_name, opponent_name,
                                   log_text=f"{html.escape(my_name)} used {html.escape(z_move_name)} for {damage} damage! KO!")
            return

        # Continue battle - opponent's turn
        c_row = get_pokemon_row(challenger_id, battle["challenger_poke_id"])
        o_row = get_pokemon_row(opponent_id, battle["opponent_poke_id"])
        c_info_r = poke_data.get_base_stats_types_sprites(c_row["pokemon_id"])
        o_info_r = poke_data.get_base_stats_types_sprites(o_row["pokemon_id"])
        c_stats_r = poke_data.calculate_stats(c_info_r["stats"], c_row["level"], row_ivs(c_row), c_row["nature"], get_evs(c_row))
        o_stats_r = poke_data.calculate_stats(o_info_r["stats"], o_row["level"], row_ivs(o_row), o_row["nature"], get_evs(o_row))

        battle_img = create_pvp_battle_image(
            c_info_r, o_info_r,
            battle["challenger_hp"], c_stats_r["hp"],
            battle["opponent_hp"], o_stats_r["hp"],
            c_row["level"], o_row["level"],
            challenger_name, opponent_name,
            challenger_transformed=battle["challenger_transformed"],
            opponent_transformed=battle["opponent_transformed"],
        )

        next_is_challenger = not is_challenger
        next_row = o_row if is_challenger else c_row
        next_info_r = o_info_r if is_challenger else c_info_r
        next_name = opponent_name if is_challenger else challenger_name
        next_role = "o" if is_challenger else "c"
        opp_for_next = c_row if is_challenger else o_row
        opp_info_next = c_info_r if is_challenger else o_info_r

        next_mega = get_player_mega_stone(opponent_id if is_challenger else challenger_id, next_info_r["name"])
        next_z = get_player_z_crystal(opponent_id if is_challenger else challenger_id, next_info_r["types"])
        next_mega_used = battle["opponent_mega_used"] if is_challenger else battle["challenger_mega_used"]
        next_z_used = battle["opponent_z_used"] if is_challenger else battle["challenger_z_used"]
        next_team = json.loads(battle["opponent_team"] if is_challenger else battle["challenger_team"])

        next_caption = build_battle_move_text(
            battle, next_row, next_info_r, opp_for_next, opp_info_next,
            next_is_challenger, next_name
        )

        next_kb = build_pvp_move_keyboard(
            battle_id, next_row, next_is_challenger,
            mega_stone=next_mega if not next_mega_used else None,
            z_crystal=next_z if not next_z_used else None,
            mega_used=next_mega_used, z_used=next_z_used,
            my_team_size=len(next_team),
        )

        z_full_caption = f"⚡ Z-Move used!\n\n{next_caption}\n\n<b>{html.escape(next_name)}'s turn!</b>"
        try:
            await query.edit_message_media(
                media=InputMediaPhoto(image_output(battle_img, "z_battle.png"),
                                      caption=z_full_caption,
                                      parse_mode=ParseMode.HTML),
                reply_markup=next_kb,
            )
        except Exception:
            try:
                await query.edit_message_caption(caption=z_full_caption, parse_mode=ParseMode.HTML, reply_markup=next_kb)
            except Exception:
                await query.message.reply_text(z_full_caption, parse_mode=ParseMode.HTML, reply_markup=next_kb)
        return

    if action == "move":
        move_index = safe_int(extra, 0)
        moves = json.loads(my_row["moves_learned"])
        move_name = moves[move_index] if move_index < len(moves) else moves[0]

        # Get move details
        try:
            move = poke_data.get_move_details(move_name)
        except Exception:
            move = {"power": 40, "type": "normal", "category": "physical", "accuracy": 100, "pp": 10, "name": move_name}

        # Accuracy check
        accuracy = move.get("accuracy", 100)
        is_crit = False
        if accuracy is not None and accuracy < 100 and random.randint(1, 100) > accuracy:
            # Move missed
            missed = True
            damage = 0
            multi = 1
        else:
            missed = False
            # Get ability for attacker and defender
            my_ability = my_info["abilities"][0] if my_info.get("abilities") else None
            opp_ability = opp_info["abilities"][0] if opp_info.get("abilities") else None

            # Apply mega stat boosts if transformed
            effective_my_stats = my_stats
            if my_transformed and my_info["name"] in MEGA_EVOLUTIONS:
                try:
                    mega_form, stat_boosts = MEGA_EVOLUTIONS[my_info["name"]]
                    m_info = poke_data.get_base_stats_types_sprites(mega_form)
                    effective_my_stats = poke_data.calculate_stats(m_info["stats"], my_row["level"], row_ivs(my_row), my_row["nature"], get_evs(my_row))
                except Exception:
                    pass

            damage, multi, is_crit = simple_damage(
                my_row["level"], effective_my_stats, opp_stats, move, opp_info["types"],
                attacker_ability=my_ability,
                defender_ability=opp_ability,
                attacker_types=my_info["types"]
            )

        move_display = move_name.replace("-", " ").title()
        move_category = move.get("category", "physical")

        if missed:
            log_lines.append(f"<b>{html.escape(my_name)}</b> used <b>{html.escape(move_display)}</b> but it missed!")
        elif move_category == "status" or damage == 0:
            log_lines.append(f"<b>{html.escape(my_name)}</b> used <b>{html.escape(move_display)}</b>!")
            if multi == 0:
                log_lines.append("It had no effect. 🚫")
            else:
                log_lines.append("The move had no direct damage effect.")
        else:
            log_lines.append(f"<b>{html.escape(my_name)}</b> used <b>{html.escape(move_display)}</b> and dealt <b>{damage}</b> damage!")
            if is_crit:
                log_lines.append("🎯 A critical hit! 💥")
            if multi > 1:
                log_lines.append("It was super effective! ⚡")
            elif multi == 0:
                log_lines.append("It had no effect. 🚫")
            elif multi < 1:
                log_lines.append("It was not very effective...")

        new_opp_hp = max(0, opp_hp - damage)

        if new_opp_hp <= 0:
            await _handle_pvp_win(
                query, context, battle, battle_id, is_challenger,
                challenger_id, opponent_id, challenger_name, opponent_name,
                log_text="\n".join(log_lines) + "\n\nOpponent's Pokémon fainted!"
            )
            return

        # Update HP and swap turn
        if is_challenger:
            update_pvp_battle(battle_id, opponent_hp=new_opp_hp, current_turn=1)
        else:
            update_pvp_battle(battle_id, challenger_hp=new_opp_hp, current_turn=0)

        battle = get_pvp_battle(battle_id)

        # Reload for updated state
        c_row = get_pokemon_row(challenger_id, battle["challenger_poke_id"])
        o_row = get_pokemon_row(opponent_id, battle["opponent_poke_id"])
        c_info_r = poke_data.get_base_stats_types_sprites(c_row["pokemon_id"])
        o_info_r = poke_data.get_base_stats_types_sprites(o_row["pokemon_id"])
        c_stats_r = poke_data.calculate_stats(c_info_r["stats"], c_row["level"], row_ivs(c_row), c_row["nature"], get_evs(c_row))
        o_stats_r = poke_data.calculate_stats(o_info_r["stats"], o_row["level"], row_ivs(o_row), o_row["nature"], get_evs(o_row))

        battle_img = create_pvp_battle_image(
            c_info_r, o_info_r,
            battle["challenger_hp"], c_stats_r["hp"],
            battle["opponent_hp"], o_stats_r["hp"],
            c_row["level"], o_row["level"],
            challenger_name, opponent_name,
            challenger_transformed=battle["challenger_transformed"],
            opponent_transformed=battle["opponent_transformed"],
        )

        # Next player's turn
        next_is_challenger = not is_challenger
        next_row = o_row if is_challenger else c_row
        next_info_r = o_info_r if is_challenger else c_info_r
        next_name = opponent_name if is_challenger else challenger_name
        opp_for_next = c_row if is_challenger else o_row
        opp_info_next = c_info_r if is_challenger else o_info_r

        next_mega = get_player_mega_stone(opponent_id if is_challenger else challenger_id, next_info_r["name"])
        next_z = get_player_z_crystal(opponent_id if is_challenger else challenger_id, next_info_r["types"])
        next_mega_used = battle["opponent_mega_used"] if is_challenger else battle["challenger_mega_used"]
        next_z_used = battle["opponent_z_used"] if is_challenger else battle["challenger_z_used"]
        next_team = json.loads(battle["opponent_team"] if is_challenger else battle["challenger_team"])

        next_caption = build_battle_move_text(
            battle, next_row, next_info_r, opp_for_next, opp_info_next,
            next_is_challenger, next_name
        )

        next_kb = build_pvp_move_keyboard(
            battle_id, next_row, next_is_challenger,
            mega_stone=next_mega if not next_mega_used else None,
            z_crystal=next_z if not next_z_used else None,
            mega_used=next_mega_used, z_used=next_z_used,
            my_team_size=len(next_team),
        )

        log_text = "\n".join(log_lines)
        full_caption = f"{log_text}\n\n{next_caption}\n\n<b>{html.escape(next_name)}'s turn!</b>"

        try:
            await query.edit_message_media(
                media=InputMediaPhoto(image_output(battle_img, "battle_turn.png"),
                                      caption=full_caption, parse_mode=ParseMode.HTML),
                reply_markup=next_kb,
            )
        except Exception:
            try:
                await query.edit_message_caption(caption=full_caption, parse_mode=ParseMode.HTML, reply_markup=next_kb)
            except Exception:
                await query.message.reply_text(full_caption, parse_mode=ParseMode.HTML, reply_markup=next_kb)


async def _handle_pvp_win(query, context, battle, battle_id, is_challenger,
                           challenger_id, opponent_id, challenger_name, opponent_name,
                           log_text=""):
    """Handle a PvP battle win."""
    winner_id = challenger_id if is_challenger else opponent_id
    loser_id = opponent_id if is_challenger else challenger_id
    winner_name = challenger_name if is_challenger else opponent_name

    update_pvp_battle(battle_id, status="ended")

    winner_user = get_user(winner_id)
    loser_user = get_user(loser_id)
    update_user(winner_id, coins=winner_user["coins"] + 200, wins=(winner_user["wins"] or 0) + 1)
    update_user(loser_id, losses=(loser_user["losses"] or 0) + 1)

    winner_team = json.loads(battle["challenger_team"] if is_challenger else battle["opponent_team"])
    winner_poke_row = get_pokemon_row(winner_id, winner_team[0])
    if winner_poke_row:
        gain_exp(winner_poke_row["id"], 200)
        winner_info = poke_data.get_base_stats_types_sprites(winner_poke_row["pokemon_id"])
        winner_stats = poke_data.calculate_stats(winner_info["stats"], winner_poke_row["level"], row_ivs(winner_poke_row), winner_poke_row["nature"], get_evs(winner_poke_row))
        win_hp = battle["challenger_hp"] if is_challenger else battle["opponent_hp"]

        try:
            win_img = create_win_image(winner_name, winner_id, winner_team, winner_info, win_hp, winner_stats["hp"])
            await query.message.reply_photo(
                InputFile(win_img, filename="winner.png"),
                caption=f"🏆 <b>{html.escape(winner_name)}</b> wins!\n<b>+200 PD</b> reward!",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass

    win_text = f"{log_text}\n\n🏆 <b>{html.escape(winner_name)}</b> wins the battle and earns <b>200 PD</b>!"
    try:
        await query.edit_message_caption(caption=win_text, parse_mode=ParseMode.HTML)
    except Exception:
        try:
            await query.edit_message_text(win_text, parse_mode=ParseMode.HTML)
        except Exception:
            await query.message.reply_text(win_text, parse_mode=ParseMode.HTML)


TM_LIST = ["TM thunderbolt", "TM flamethrower", "TM ice-beam", "TM earthquake", "TM psychic"]
MEGA_STONE_LIST = list(MEGA_STONE_POKE.keys())
Z_STONE_LIST = list(Z_CRYSTALS.keys())
RANDOM_POKE_IDS = list(range(1, 152))


def parse_rewards(reward_str):
    """Parse reward string like '100pd,random(poke),tm(random),mega(random),zstone(random)'
    Returns a list of reward dicts and a human-readable summary."""
    rewards = []
    summary_parts = []
    for part in reward_str.split(","):
        part = part.strip().lower()
        if not part:
            continue

        # PokéDollars: e.g. 100pd
        if part.endswith("pd") and part[:-2].isdigit():
            amount = int(part[:-2])
            rewards.append({"type": "pd", "amount": amount})
            summary_parts.append(f"💰 {amount} PD")

        # Random pokémon: random(poke)
        elif part.startswith("random(poke") or part == "random(pokemon)":
            poke_id = random.choice(RANDOM_POKE_IDS)
            rewards.append({"type": "poke", "poke_id": poke_id})
            summary_parts.append("🎲 Random Pokémon")

        # TM: tm(random) or tm(thunderbolt)
        elif part.startswith("tm("):
            inner = part[3:].rstrip(")")
            if inner == "random":
                tm = random.choice(TM_LIST)
            else:
                tm = f"TM {inner}" if not inner.startswith("tm ") else inner
                if tm not in TM_LIST:
                    tm = random.choice(TM_LIST)
            rewards.append({"type": "item", "item": tm, "qty": 1})
            summary_parts.append(f"📀 {tm}")

        # Mega stone: mega(random) or mega(Lucarionite)
        elif part.startswith("mega("):
            inner = part[5:].rstrip(")")
            if inner == "random":
                stone = random.choice(MEGA_STONE_LIST)
            else:
                stone = inner.title()
                if stone not in MEGA_STONE_LIST:
                    stone = random.choice(MEGA_STONE_LIST)
            rewards.append({"type": "item", "item": stone, "qty": 1})
            summary_parts.append(f"💎 {stone}")

        # Z-stone: zstone(random) or zstone(Firium Z)
        elif part.startswith("zstone("):
            inner = part[7:].rstrip(")")
            if inner == "random":
                zstone = random.choice(Z_STONE_LIST)
            else:
                zstone = inner.title()
                if zstone not in Z_STONE_LIST:
                    zstone = random.choice(Z_STONE_LIST)
            rewards.append({"type": "item", "item": zstone, "qty": 1})
            summary_parts.append(f"🔮 {zstone}")

    return rewards, summary_parts


async def give_rewards(user_id, rewards):
    """Apply reward list to a user. Returns list of result strings."""
    results = []
    user = get_user(user_id)
    if not user:
        return ["❌ User not found."]

    for r in rewards:
        if r["type"] == "pd":
            update_user(user_id, coins=user["coins"] + r["amount"])
            user = get_user(user_id)
            results.append(f"💰 +{r['amount']} PokéDollars")

        elif r["type"] == "poke":
            poke_id = r["poke_id"]
            try:
                info = poke_data.get_base_stats_types_sprites(poke_id)
                row_id = add_caught_pokemon(user_id, poke_id, level=random.randint(10, 50))
                results.append(f"🎁 Got a <b>{info['name'].title()}</b>!")
            except Exception:
                results.append("🎁 Got a mystery Pokémon!")

        elif r["type"] == "item":
            add_item(user_id, r["item"], r["qty"])
            results.append(f"📦 +{r['qty']}x <b>{r['item']}</b>")

    return results


async def create_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if BOT_OWNER_ID and user_id != BOT_OWNER_ID:
        await update.message.reply_text("❌ Only the bot owner can use this command.")
        return

    if not context.args:
        await update.message.reply_text(
            "📋 <b>Create Redeem Code</b>\n\n"
            "<b>Usage:</b> /create &lt;rewards&gt; [uses=N]\n\n"
            "<b>Reward types:</b>\n"
            "• <code>100pd</code> — PokéDollars\n"
            "• <code>random(poke)</code> — Random Pokémon\n"
            "• <code>tm(random)</code> — Random TM\n"
            "• <code>mega(random)</code> — Random Mega Stone\n"
            "• <code>zstone(random)</code> — Random Z-Crystal\n\n"
            "<b>Examples:</b>\n"
            "<code>/create 500pd,random(poke)</code>\n"
            "<code>/create 100pd,tm(random),mega(random) uses=10</code>\n"
            "<code>/create random(poke),zstone(random) uses=50</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    args = " ".join(context.args)

    # Check for uses=N at the end
    max_uses = 1
    if "uses=" in args:
        parts = args.rsplit("uses=", 1)
        args = parts[0].strip().rstrip()
        try:
            max_uses = max(1, int(parts[1].strip()))
        except ValueError:
            max_uses = 1

    rewards, summary_parts = parse_rewards(args)
    if not rewards:
        await update.message.reply_text("❌ No valid rewards found. Check the format and try again.")
        return

    code = "PKM-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))

    create_redeem_code(code, json.dumps(rewards), max_uses)

    await update.message.reply_text(
        f"✅ <b>Redeem Code Created!</b>\n\n"
        f"🎟️ Code: <code>{code}</code>\n"
        f"🎁 Rewards:\n" + "\n".join(f"  • {s}" for s in summary_parts) + "\n"
        f"♻️ Max uses: <b>{max_uses}</b>\n\n"
        f"Players can redeem with: /redeem {code}",
        parse_mode=ParseMode.HTML,
    )


async def redeem_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("❌ You need to /start the bot first!")
        return

    if not context.args:
        await update.message.reply_text(
            "🎟️ Usage: /redeem &lt;CODE&gt;\n\nExample: /redeem PKM-ABCD1234",
            parse_mode=ParseMode.HTML,
        )
        return

    code = context.args[0].strip().upper()
    row = get_redeem_code(code)

    if not row:
        await update.message.reply_text("❌ Invalid code. Please check and try again.")
        return

    used_by = json.loads(row["used_by"])
    if user_id in used_by:
        await update.message.reply_text("❌ You have already used this code!")
        return

    if len(used_by) >= row["max_uses"]:
        await update.message.reply_text("❌ This code has already been fully redeemed.")
        return

    rewards = json.loads(row["rewards"])
    results = await give_rewards(user_id, rewards)
    mark_code_used(code, user_id)

    uses_left = row["max_uses"] - len(used_by) - 1
    await update.message.reply_text(
        f"🎉 <b>Code Redeemed Successfully!</b>\n\n"
        f"🎁 <b>Your Rewards:</b>\n" + "\n".join(f"  • {r}" for r in results) + "\n\n"
        f"♻️ Uses remaining: <b>{uses_left}</b>",
        parse_mode=ParseMode.HTML,
    )


async def admin_add_poke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if BOT_OWNER_ID and user_id != BOT_OWNER_ID:
        await update.message.reply_text("❌ Only the bot owner can use this command.")
        return

    usage = (
        "📋 <b>Add Pokémon to Player</b>\n\n"
        "<b>Usage:</b>\n"
        "<code>/add &lt;user_id&gt; &lt;pokemon&gt; &lt;nature&gt; &lt;ivs&gt; &lt;level&gt;</code>\n\n"
        "<b>IVs:</b> 6 values 0–31 separated by commas\n"
        "  (hp, atk, def, sp.atk, sp.def, speed)\n\n"
        "<b>Example:</b>\n"
        "<code>/add 123456789 pikachu adamant 31,31,31,31,31,31 50</code>\n\n"
        "<b>Tip:</b> Reply to a user's message instead of typing their ID."
    )

    # Resolve target user — either from reply or first arg
    args = list(context.args or [])
    target_id = None

    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
    elif args and args[0].lstrip("-").isdigit():
        target_id = int(args.pop(0))
    else:
        await update.message.reply_text(usage, parse_mode=ParseMode.HTML)
        return

    if len(args) < 4:
        await update.message.reply_text(usage, parse_mode=ParseMode.HTML)
        return

    poke_name = args[0].lower().strip()
    nature_input = args[1].strip().title()
    ivs_input = args[2].strip()
    level_input = args[3].strip()

    # Validate nature
    if nature_input not in NATURES:
        valid = ", ".join(NATURES.keys())
        await update.message.reply_text(
            f"❌ Invalid nature <b>{html.escape(nature_input)}</b>.\n\n"
            f"Valid natures:\n<code>{html.escape(valid)}</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    # Validate IVs
    try:
        ivs = [int(v.strip()) for v in ivs_input.split(",")]
        if len(ivs) != 6 or any(v < 0 or v > 31 for v in ivs):
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "❌ IVs must be 6 comma-separated values between 0 and 31.\n"
            "Example: <code>31,31,31,31,31,31</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    # Validate level
    try:
        level = int(level_input)
        if level < 1 or level > 100:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Level must be a number between 1 and 100.")
        return

    # Validate target user exists in bot
    target_user = get_user(target_id)
    if not target_user:
        await update.message.reply_text(
            f"❌ User <code>{target_id}</code> has not started the bot yet.",
            parse_mode=ParseMode.HTML,
        )
        return

    # Fetch Pokémon from PokeAPI
    try:
        info = poke_data.get_base_stats_types_sprites(poke_name)
    except Exception:
        await update.message.reply_text(
            f"❌ Pokémon <b>{html.escape(poke_name)}</b> not found. Check the spelling and try again.",
            parse_mode=ParseMode.HTML,
        )
        return

    poke_id = info["id"]
    poke_display = info["name"]
    types_str = ", ".join(t.title() for t in info["types"])

    iv_labels = ["HP", "Atk", "Def", "Sp.Atk", "Sp.Def", "Spd"]
    iv_display = " / ".join(f"{label}:{v}" for label, v in zip(iv_labels, ivs))

    add_caught_pokemon_custom(
        target_id, poke_id, info["name"], level, nature_input, ivs
    )

    await update.message.reply_text(
        f"✅ <b>Pokémon Added!</b>\n\n"
        f"🎁 <b>{html.escape(poke_display)}</b> added to user <code>{target_id}</code>\n"
        f"━━━━━━━━━━━━━━\n"
        f"🏷️ Nature: <b>{nature_input}</b>\n"
        f"⚡ Type: <b>{html.escape(types_str)}</b>\n"
        f"📊 IVs: <code>{html.escape(iv_display)}</code>\n"
        f"🎚️ Level: <b>{level}</b>",
        parse_mode=ParseMode.HTML,
    )


async def gyms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏟️ <b>Gyms</b>\n\n"
        "⚒️ This feature is currently under construction.\n"
        "Gym battles are <b>coming soon</b>! Stay tuned! 🚀",
        parse_mode=ParseMode.HTML,
    )


async def track_group_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.my_chat_member
    if not result:
        return
    chat = result.chat
    if chat.type not in ("group", "supergroup"):
        return
    new_status = result.new_chat_member.status
    if new_status in ("member", "administrator"):
        save_group(chat.id, chat.title or "")
    elif new_status in ("left", "kicked", "banned"):
        remove_group(chat.id)


async def bordchast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if BOT_OWNER_ID and user_id != BOT_OWNER_ID:
        await update.message.reply_text("❌ Only the bot owner can use this command.")
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: /bordchast <message>\n\nExample: /bordchast Hello everyone! 🎉"
        )
        return

    text = " ".join(context.args)
    broadcast_text = f"📢 <b>Broadcast Message</b>\n\n{html.escape(text)}"

    users = get_all_user_ids()
    groups = get_all_groups()
    total = len(users) + len(groups)

    status_msg = await update.message.reply_text(
        f"📡 Sending to {len(users)} users and {len(groups)} groups..."
    )

    sent = 0
    failed = 0

    for row in users:
        try:
            await context.bot.send_message(
                chat_id=row["user_id"],
                text=broadcast_text,
                parse_mode=ParseMode.HTML,
            )
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)

    for row in groups:
        try:
            await context.bot.send_message(
                chat_id=row["chat_id"],
                text=broadcast_text,
                parse_mode=ParseMode.HTML,
            )
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)

    try:
        await status_msg.edit_text(
            f"✅ Broadcast complete!\n\n"
            f"📨 Sent: {sent}/{total}\n"
            f"❌ Failed: {failed}"
        )
    except Exception:
        pass


async def pokerandom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚔️ Want a random Pokémon battle?\n\nContinue with this bot: @Pokerandombattlebot for random battle!"
    )


async def travel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = ensure_started(update)
    if not context.args:
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(r, callback_data=f"travel:{r}") for r in list(REGIONS.keys())[i : i + 3]] for i in range(0, len(REGIONS), 3)])
        await update.message.reply_text("Choose region or use /travel Kanto:", reply_markup=keyboard)
        return
    region = context.args[0].title()
    if region not in REGIONS:
        await update.message.reply_text("Regions: " + ", ".join(REGIONS.keys()))
        return
    update_user(user_id, current_region=region)
    await update.message.reply_text(f"Travel complete. Current region: {region}. /hunt now uses that region pool.")


async def travel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = ensure_started(update)
    region = query.data.split(":", 1)[1]
    update_user(user_id, current_region=region)
    await query.edit_message_text(f"Travel complete. Current region: {region}. /hunt now uses that region pool.")


SHOP_BANNER = "https://files.catbox.moe/fxmt57.jpg"

SHOP_CATEGORIES = {
    "pokeballs": {
        "label": "🔴 Pokéballs",
        "emoji": "🔴",
        "items": ["Pokeball", "Great Ball", "Ultra Ball"],
    },
    "candy": {
        "label": "🍬 Candy & Vitamins",
        "emoji": "🍬",
        "items": ["Rare Candy", "Level Candy", "Vitamin", "Berry"],
    },
    "stones": {
        "label": "💎 Evolution Stones",
        "emoji": "💎",
        "items": ["Fire Stone", "Water Stone", "Thunder Stone", "Leaf Stone", "Moon Stone", "Sun Stone", "Ice Stone", "Dawn Stone", "Dusk Stone", "Shiny Stone"],
    },
    "mega": {
        "label": "💜 Mega Stones",
        "emoji": "💜",
        "items": ["Charizardite X", "Lucarionite"],
    },
    "zcrystal": {
        "label": "💛 Z-Crystals",
        "emoji": "💛",
        "items": ["Z Ring", "Firium Z", "Waterium Z", "Electrium Z", "Grassium Z"],
    },
    "tms": {
        "label": "💿 TMs",
        "emoji": "💿",
        "items": ["TM thunderbolt", "TM flamethrower", "TM ice-beam", "TM earthquake", "TM psychic"],
    },
}


def shop_main_keyboard():
    rows = []
    cats = list(SHOP_CATEGORIES.items())
    for i in range(0, len(cats), 2):
        row = []
        for key, cat in cats[i:i+2]:
            row.append(InlineKeyboardButton(cat["label"], callback_data=f"shop:{key}"))
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def shop_category_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Shop", callback_data="shop:main")]])


def build_shop_category_text(category, user_coins):
    cat = SHOP_CATEGORIES.get(category)
    if not cat:
        return "Category not found."
    lines = [f"{cat['emoji']} <b>{cat['label']}</b>\n"]
    for item in cat["items"]:
        price = SHOP_ITEMS.get(item)
        if price is None:
            continue
        extra = item_detail(item)
        affordable = "✅" if user_coins >= price else "❌"
        if item in MEGA_STONES or item in Z_CRYSTALS:
            lines.append(f"{affordable} <b>{html.escape(item)}</b> — <code>{price} PD</code>\n     ↳ {html.escape(extra)}")
        else:
            lines.append(f"{affordable} <b>{html.escape(item)}</b> — <code>{price} PD</code>")
    lines.append(f"\n💰 Your PD: <b>{user_coins}</b>")
    lines.append("\n<i>Buy with /buy &lt;item&gt; &lt;qty&gt;</i>")
    lines.append("<i>Example: /buy Pokeball 5</i>")
    return "\n".join(lines)


async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = ensure_started(update)
    user = get_user(user_id)
    caption = (
        "🏪 <b>Welcome to the Pokémon Shop!</b>\n\n"
        f"💰 Your PokéDollars: <b>{user['coins']} PD</b>\n\n"
        "Browse a category below to see items and prices.\n"
        "Buy with: <code>/buy &lt;item&gt; &lt;quantity&gt;</code>"
    )
    try:
        await update.message.reply_photo(
            SHOP_BANNER,
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=shop_main_keyboard(),
        )
    except Exception:
        await update.message.reply_text(caption, parse_mode=ParseMode.HTML, reply_markup=shop_main_keyboard())


async def shop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = ensure_started(update)
    user = get_user(user_id)
    category = query.data.split(":", 1)[1]
    if category == "main":
        caption = (
            "🏪 <b>Welcome to the Pokémon Shop!</b>\n\n"
            f"💰 Your PokéDollars: <b>{user['coins']} PD</b>\n\n"
            "Browse a category below to see items and prices.\n"
            "Buy with: <code>/buy &lt;item&gt; &lt;quantity&gt;</code>"
        )
        try:
            await query.edit_message_caption(caption=caption, parse_mode=ParseMode.HTML, reply_markup=shop_main_keyboard())
        except Exception:
            await query.edit_message_text(caption, parse_mode=ParseMode.HTML, reply_markup=shop_main_keyboard())
        return
    text = build_shop_category_text(category, user["coins"])
    try:
        await query.edit_message_caption(caption=text, parse_mode=ParseMode.HTML, reply_markup=shop_category_keyboard())
    except Exception:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=shop_category_keyboard())


async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = ensure_started(update)
    if len(context.args) < 2:
        await update.message.reply_text("Use: /buy Pokeball 5 or /buy TM thunderbolt 1")
        return
    qty = safe_int(context.args[-1], 1)
    item = " ".join(context.args[:-1]).strip()
    normalized = next((k for k in SHOP_ITEMS if k.lower() == item.lower()), None)
    if not normalized:
        await update.message.reply_text("Item not found. Use /shop.")
        return
    qty = max(1, min(99, qty))
    cost = SHOP_ITEMS[normalized] * qty
    user = get_user(user_id)
    if user["coins"] < cost:
        await update.message.reply_text(f"Not enough PD. Need {cost}, you have {user['coins']}.")
        return
    update_user(user_id, coins=user["coins"] - cost)
    add_item(user_id, normalized, qty)
    await update.message.reply_text(f"Bought {normalized} × {qty} for {cost} PD.")


def build_candy_text(user_id, row):
    rc = get_item_qty(user_id, "Rare Candy")
    lc = get_item_qty(user_id, "Level Candy")
    name = html.escape(display_name(row))
    return (
        f"<b>🍬 Use Candy on {name}</b>\n\n"
        f"Current Level: <b>Lv. {row['level']}</b>\n\n"
        f"🍬 <b>Rare Candy</b> × {rc}  (+3 levels each)\n"
        f"🍭 <b>Level Candy</b> × {lc}  (+1 level each)\n\n"
        f"<i>Select how many to use:</i>"
    )


def build_candy_keyboard(caught_id, has_rare, has_level):
    rows = []
    if has_rare > 0:
        rows.append([
            InlineKeyboardButton(f"🍬 +1 Rare ({min(1,has_rare)})", callback_data=f"candy:{caught_id}:rare:1"),
            InlineKeyboardButton(f"+5 Rare", callback_data=f"candy:{caught_id}:rare:5"),
            InlineKeyboardButton(f"+10 Rare", callback_data=f"candy:{caught_id}:rare:10"),
        ])
    if has_level > 0:
        rows.append([
            InlineKeyboardButton(f"🍭 +1 Lvl ({min(1,has_level)})", callback_data=f"candy:{caught_id}:level:1"),
            InlineKeyboardButton(f"+5 Lvl", callback_data=f"candy:{caught_id}:level:5"),
            InlineKeyboardButton(f"+10 Lvl", callback_data=f"candy:{caught_id}:level:10"),
        ])
    rows.append([InlineKeyboardButton("✖️ Close", callback_data=f"candy:{caught_id}:close")])
    return InlineKeyboardMarkup(rows)


async def candy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = ensure_started(update)
    if not context.args:
        await update.message.reply_text("Use: /candy <Pokémon name or ID>\nExample: /candy Charmander")
        return
    query = " ".join(context.args)
    caught_id = safe_int(query)
    if caught_id:
        row = get_pokemon_row(user_id, caught_id)
    else:
        row = find_owned_pokemon(user_id, query)
    if not row:
        await update.message.reply_text(f"You don't own a Pokémon matching '{query}'.")
        return
    rc = get_item_qty(user_id, "Rare Candy")
    lc = get_item_qty(user_id, "Level Candy")
    if rc == 0 and lc == 0:
        await update.message.reply_text("You have no candy! Buy some in /shop.")
        return
    text = build_candy_text(user_id, row)
    keyboard = build_candy_keyboard(row["id"], rc, lc)
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


async def candy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = ensure_started(update)
    parts = query.data.split(":")
    caught_id = safe_int(parts[1])
    row = get_pokemon_row(user_id, caught_id)
    if not row:
        await query.edit_message_text("Pokémon not found.")
        return
    action = parts[2]
    if action == "close":
        await query.edit_message_text("Candy menu closed.")
        return
    qty = safe_int(parts[3], 1)
    item = "Rare Candy" if action == "rare" else "Level Candy"
    owned = get_item_qty(user_id, item)
    qty = min(qty, owned)
    if qty <= 0:
        await query.answer(f"You don't have enough {item}!", show_alert=True)
        return
    level_gain = qty * 3 if item == "Rare Candy" else qty
    use_item(user_id, item, qty)
    with db() as conn:
        conn.execute("UPDATE caught_pokemon SET level = MIN(100, level + ?) WHERE id = ? AND user_id = ?", (level_gain, caught_id, user_id))
    row = get_pokemon_row(user_id, caught_id)
    rc = get_item_qty(user_id, "Rare Candy")
    lc = get_item_qty(user_id, "Level Candy")
    text = build_candy_text(user_id, row)
    text += f"\n\n✅ Used {qty}× {item} → <b>+{level_gain} levels!</b> Now Lv. {row['level']}"
    keyboard = build_candy_keyboard(row["id"], rc, lc)
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


def build_ev_text(user_id, row, mode="vitamin"):
    evs = get_evs(row)
    total = ev_total(evs)
    item = "Vitamin" if mode == "vitamin" else "Berry"
    owned = get_item_qty(user_id, item)
    emoji = "🧴" if mode == "vitamin" else "🫐"
    action = "increase" if mode == "vitamin" else "decrease"
    name = html.escape(display_name(row))
    lines = [
        f"<b>{emoji} {item} — {name}</b>\n",
        f"Level: <b>Lv. {row['level']}</b>   {emoji} Owned: <b>{owned}</b>",
        f"Total EVs: <b>{total}/{EV_MAX_TOTAL}</b>\n",
        "<b>Current EVs:</b>",
    ]
    for stat in EV_STATS:
        bar = "▓" * (evs[stat] // 26) + "░" * (10 - evs[stat] // 26)
        lines.append(f"  {EV_STAT_LABELS[stat]:8s} {bar} {evs[stat]}/252")
    lines.append(f"\n<i>Tap a stat to {action} its EVs (1 {item} = 10 EVs)</i>")
    return "\n".join(lines)


def build_ev_stat_keyboard(caught_id, mode):
    emoji = "🧴" if mode == "vitamin" else "🫐"
    rows = []
    stat_row = []
    for i, stat in enumerate(EV_STATS):
        stat_row.append(InlineKeyboardButton(f"{emoji} {EV_STAT_LABELS[stat]}", callback_data=f"{mode}:{caught_id}:stat:{stat}"))
        if len(stat_row) == 3:
            rows.append(stat_row)
            stat_row = []
    if stat_row:
        rows.append(stat_row)
    rows.append([InlineKeyboardButton("✖️ Close", callback_data=f"{mode}:{caught_id}:close")])
    return InlineKeyboardMarkup(rows)


def build_ev_qty_keyboard(caught_id, stat, mode):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("+1", callback_data=f"{mode}:{caught_id}:apply:{stat}:1"),
            InlineKeyboardButton("+5", callback_data=f"{mode}:{caught_id}:apply:{stat}:5"),
            InlineKeyboardButton("+10", callback_data=f"{mode}:{caught_id}:apply:{stat}:10"),
        ],
        [InlineKeyboardButton("⬅️ Back", callback_data=f"{mode}:{caught_id}:back")],
    ])


async def vitamin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = ensure_started(update)
    if not context.args:
        await update.message.reply_text("Use: /vitamin <Pokémon name or ID>\nExample: /vitamin Charmander")
        return
    query_str = " ".join(context.args)
    caught_id = safe_int(query_str)
    row = get_pokemon_row(user_id, caught_id) if caught_id else find_owned_pokemon(user_id, query_str)
    if not row:
        await update.message.reply_text(f"You don't own a Pokémon matching '{query_str}'.")
        return
    if get_item_qty(user_id, "Vitamin") == 0:
        await update.message.reply_text("You have no Vitamins! Buy some in /shop.")
        return
    text = build_ev_text(user_id, row, "vitamin")
    keyboard = build_ev_stat_keyboard(row["id"], "vitamin")
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


async def vitamin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = ensure_started(update)
    parts = query.data.split(":")
    caught_id = safe_int(parts[1])
    row = get_pokemon_row(user_id, caught_id)
    if not row:
        await query.edit_message_text("Pokémon not found.")
        return
    action = parts[2]
    if action == "close":
        await query.edit_message_text("Vitamin menu closed.")
        return
    if action == "back":
        text = build_ev_text(user_id, row, "vitamin")
        keyboard = build_ev_stat_keyboard(caught_id, "vitamin")
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        return
    if action == "stat":
        stat = parts[3]
        evs = get_evs(row)
        owned = get_item_qty(user_id, "Vitamin")
        label = EV_STAT_LABELS.get(stat, stat)
        text = (
            f"<b>🧴 Vitamin — {html.escape(display_name(row))}</b>\n\n"
            f"Stat: <b>{label}</b>  Current EVs: <b>{evs[stat]}/252</b>\n"
            f"Total EVs: <b>{ev_total(evs)}/{EV_MAX_TOTAL}</b>\n"
            f"🧴 Vitamins owned: <b>{owned}</b>\n\n"
            f"Each Vitamin adds <b>10 EVs</b>. Choose quantity:"
        )
        keyboard = build_ev_qty_keyboard(caught_id, stat, "vitamin")
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        return
    if action == "apply":
        stat = parts[3]
        qty = safe_int(parts[4], 1)
        evs = get_evs(row)
        owned = get_item_qty(user_id, "Vitamin")
        qty = min(qty, owned)
        if qty <= 0:
            await query.answer("No Vitamins left!", show_alert=True)
            return
        total = ev_total(evs)
        room_total = EV_MAX_TOTAL - total
        room_stat = EV_MAX_STAT - evs[stat]
        max_usable = min(qty, room_total // 10, room_stat // 10)
        if max_usable <= 0:
            await query.answer("EVs are maxed out for this stat or total!", show_alert=True)
            return
        use_item(user_id, "Vitamin", max_usable)
        evs[stat] = min(EV_MAX_STAT, evs[stat] + max_usable * 10)
        set_evs(caught_id, evs)
        row = get_pokemon_row(user_id, caught_id)
        await query.answer(f"+{max_usable * 10} EVs to {EV_STAT_LABELS[stat]}!")
        text = build_ev_text(user_id, row, "vitamin")
        keyboard = build_ev_stat_keyboard(caught_id, "vitamin")
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


async def berry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = ensure_started(update)
    if not context.args:
        await update.message.reply_text("Use: /berry <Pokémon name or ID>\nExample: /berry Charmander")
        return
    query_str = " ".join(context.args)
    caught_id = safe_int(query_str)
    row = get_pokemon_row(user_id, caught_id) if caught_id else find_owned_pokemon(user_id, query_str)
    if not row:
        await update.message.reply_text(f"You don't own a Pokémon matching '{query_str}'.")
        return
    if get_item_qty(user_id, "Berry") == 0:
        await update.message.reply_text("You have no Berries! Buy some in /shop.")
        return
    text = build_ev_text(user_id, row, "berry")
    keyboard = build_ev_stat_keyboard(row["id"], "berry")
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


async def berry_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = ensure_started(update)
    parts = query.data.split(":")
    caught_id = safe_int(parts[1])
    row = get_pokemon_row(user_id, caught_id)
    if not row:
        await query.edit_message_text("Pokémon not found.")
        return
    action = parts[2]
    if action == "close":
        await query.edit_message_text("Berry menu closed.")
        return
    if action == "back":
        text = build_ev_text(user_id, row, "berry")
        keyboard = build_ev_stat_keyboard(caught_id, "berry")
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        return
    if action == "stat":
        stat = parts[3]
        evs = get_evs(row)
        owned = get_item_qty(user_id, "Berry")
        label = EV_STAT_LABELS.get(stat, stat)
        text = (
            f"<b>🫐 Berry — {html.escape(display_name(row))}</b>\n\n"
            f"Stat: <b>{label}</b>  Current EVs: <b>{evs[stat]}/252</b>\n"
            f"Total EVs: <b>{ev_total(evs)}/{EV_MAX_TOTAL}</b>\n"
            f"🫐 Berries owned: <b>{owned}</b>\n\n"
            f"Each Berry removes <b>10 EVs</b>. Choose quantity:"
        )
        keyboard = build_ev_qty_keyboard(caught_id, stat, "berry")
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        return
    if action == "apply":
        stat = parts[3]
        qty = safe_int(parts[4], 1)
        evs = get_evs(row)
        owned = get_item_qty(user_id, "Berry")
        qty = min(qty, owned)
        if qty <= 0:
            await query.answer("No Berries left!", show_alert=True)
            return
        max_reducible = evs[stat] // 10
        max_usable = min(qty, max_reducible)
        if max_usable <= 0:
            await query.answer("No EVs to remove for this stat!", show_alert=True)
            return
        use_item(user_id, "Berry", max_usable)
        evs[stat] = max(0, evs[stat] - max_usable * 10)
        set_evs(caught_id, evs)
        row = get_pokemon_row(user_id, caught_id)
        await query.answer(f"-{max_usable * 10} EVs from {EV_STAT_LABELS[stat]}!")
        text = build_ev_text(user_id, row, "berry")
        keyboard = build_ev_stat_keyboard(caught_id, "berry")
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


async def evolve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = ensure_started(update)
    if not context.args:
        await update.message.reply_text("Use: /evolve 12 or /evolve 12 Fire Stone")
        return
    caught_id = safe_int(context.args[0])
    stone = " ".join(context.args[1:]).strip() or None
    row = get_pokemon_row(user_id, caught_id)
    if not row:
        await update.message.reply_text("Pokémon not found.")
        return
    if stone and get_item_qty(user_id, stone) <= 0:
        await update.message.reply_text(f"You do not own {stone}.")
        return
    result = poke_data.can_evolve(row["pokemon_id"], level=row["level"], stone=stone)
    if not result:
        await update.message.reply_text("This Pokémon cannot evolve right now by that level or stone.")
        return
    if stone:
        use_item(user_id, stone, 1)
    moves = poke_data.get_default_moves(result["id"], row["level"])
    with db() as conn:
        conn.execute("UPDATE caught_pokemon SET pokemon_id = ?, pokemon_name = ?, moves_learned = ? WHERE id = ? AND user_id = ?", (result["id"], result["name"], json.dumps(moves), caught_id, user_id))
    await update.message.reply_text(f"{display_name(row)} evolved into {result['name']}!")


async def rename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = ensure_started(update)
    if len(context.args) < 2:
        await update.message.reply_text("Use: /rename 12 Sparky")
        return
    caught_id = safe_int(context.args[0])
    nickname = " ".join(context.args[1:])[:30]
    row = get_pokemon_row(user_id, caught_id)
    if not row:
        await update.message.reply_text("Pokémon not found.")
        return
    with db() as conn:
        conn.execute("UPDATE caught_pokemon SET nickname = ? WHERE id = ? AND user_id = ?", (nickname, caught_id, user_id))
    await update.message.reply_text(f"Renamed {row['pokemon_name']} to {nickname}.")


async def hatch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = ensure_started(update)
    hatched = decrement_egg_steps(user_id)
    with db() as conn:
        eggs = conn.execute("SELECT * FROM eggs WHERE user_id = ? ORDER BY steps_remaining", (user_id,)).fetchall()
    lines = ["<b>Egg Hatch</b>"]
    if hatched:
        for _, caught_id, name in hatched:
            lines.append(f"Hatched <b>{html.escape(name)}</b> with high IVs. Collection ID #{caught_id}")
    if eggs:
        lines.append("\nRemaining eggs:")
        for egg in eggs:
            lines.append(f"Egg #{egg['id']} {html.escape(egg['egg_type'])}: {egg['steps_remaining']} hunts left")
    if not hatched and not eggs:
        lines.append("No eggs. You can find eggs while using /hunt.")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def run_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = ensure_started(update)
    with db() as conn:
        conn.execute("DELETE FROM active_encounters WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM battle_sessions WHERE user_id = ?", (user_id,))
        conn.execute("UPDATE pvp_battles SET status = 'ended' WHERE (challenger_id = ? OR opponent_id = ?) AND status = 'active'", (user_id, user_id))
    await update.message.reply_text("All active hunt/battle sessions cleared.")


def load_trainer_avatar(avatar_index, size=(220, 320)):
    try:
        index = max(0, min(avatar_index, len(TRAINER_AVATARS) - 1))
        url = TRAINER_AVATARS[index]["url"]
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content)).convert("RGBA")
        img.thumbnail(size, Image.Resampling.LANCZOS)
        return img
    except Exception:
        return None


def create_profile_card_image(user_id, user, count, unique_count, eggs):
    W, H = 780, 440
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    for y in range(H):
        r = int(232 - y * 0.06)
        g = int(198 - y * 0.10)
        b = int(80 + y * 0.05)
        draw.line([(0, y), (W, y)], fill=(r, g, b, 255))

    for _ in range(18):
        cx = random.randint(0, W)
        cy = random.randint(0, H)
        cr = random.randint(18, 55)
        draw.ellipse((cx - cr, cy - cr, cx + cr, cy + cr), outline=(255, 255, 200, 40), width=3)

    card_left, card_top, card_right, card_bottom = 24, 24, W - 240, H - 24
    draw.rounded_rectangle((card_left, card_top, card_right, card_bottom), radius=22, fill=(255, 255, 240, 235), outline=(210, 180, 60, 200), width=3)

    try:
        font_big = ImageFont.truetype("DejaVuSans-Bold.ttf", 28)
        font_med = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
        font_val = ImageFont.truetype("DejaVuSans.ttf", 22)
        font_small = ImageFont.truetype("DejaVuSans.ttf", 18)
        font_wins = ImageFont.truetype("DejaVuSans-Bold.ttf", 34)
        font_wins_num = ImageFont.truetype("DejaVuSans-Bold.ttf", 42)
    except Exception:
        font_big = font_med = font_val = font_small = font_wins = font_wins_num = None

    draw.text((card_left + 20, card_top + 16), f"ID: {user_id}", fill=(60, 50, 30), font=font_big)

    sep_y = card_top + 56
    draw.line([(card_left + 14, sep_y), (card_right - 14, sep_y)], fill=(180, 160, 80, 180), width=2)

    stats_y = sep_y + 16
    row_h = 46
    stats = [
        ("POKÉDEX", f"{unique_count}/1025"),
        ("CAUGHT", str(count)),
        ("REGION", user["current_region"].upper()),
        ("TOTAL PD", f"{user['coins']} PD"),
    ]
    for label, value in stats:
        draw.text((card_left + 22, stats_y + 8), label, fill=(100, 80, 30), font=font_med)
        draw.text((card_left + 200, stats_y + 8), value, fill=(50, 40, 20), font=font_val)
        draw.line([(card_left + 14, stats_y + row_h - 4), (card_right - 14, stats_y + row_h - 4)], fill=(200, 185, 100, 100), width=1)
        stats_y += row_h

    wins_x = card_left + 22
    wins_y = H - 24 - 100
    win_box_w = (card_right - card_left - 60) // 2
    draw.rounded_rectangle((wins_x, wins_y, wins_x + win_box_w, wins_y + 92), radius=14, fill=(240, 200, 30, 240))
    draw.text((wins_x + win_box_w // 2 - 38, wins_y + 6), "WINS", fill=(80, 60, 10), font=font_wins)
    wins_val = str(user["wins"] or 0)
    draw.text((wins_x + win_box_w // 2 - 18, wins_y + 44), wins_val, fill=(60, 40, 5), font=font_wins_num)

    loss_x = wins_x + win_box_w + 16
    draw.rounded_rectangle((loss_x, wins_y, loss_x + win_box_w, wins_y + 92), radius=14, fill=(140, 140, 140, 240))
    draw.text((loss_x + win_box_w // 2 - 34, wins_y + 6), "LOSS", fill=(240, 240, 240), font=font_wins)
    loss_val = str(user["losses"] or 0)
    draw.text((loss_x + win_box_w // 2 - 18, wins_y + 44), loss_val, fill=(255, 255, 255), font=font_wins_num)

    avatar_index = user["avatar_index"] or 0
    trainer = load_trainer_avatar(avatar_index, size=(210, 330))
    trainer_x = card_right + 10
    if trainer:
        paste_y = H - trainer.height - 10
        img.paste(trainer, (trainer_x, max(10, paste_y)), trainer)

    now = datetime.now().strftime("%I:%M %p")
    draw.text((card_right - 120, H - 24 - 24), now, fill=(80, 60, 20), font=font_small)

    rgb_img = Image.new("RGB", (W, H), (30, 30, 30))
    rgb_img.paste(img, mask=img.split()[3])

    output = BytesIO()
    rgb_img.save(output, format="PNG")
    output.seek(0)
    return output


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = ensure_started(update)
    user = get_user(user_id)
    with db() as conn:
        count = conn.execute("SELECT COUNT(*) AS c FROM caught_pokemon WHERE user_id = ?", (user_id,)).fetchone()["c"]
        unique_count = conn.execute("SELECT COUNT(DISTINCT pokemon_id) AS c FROM caught_pokemon WHERE user_id = ?", (user_id,)).fetchone()["c"]
        eggs = conn.execute("SELECT COUNT(*) AS c FROM eggs WHERE user_id = ?", (user_id,)).fetchone()["c"]
    image = create_profile_card_image(user_id, user, count, unique_count, eggs)
    caption = (
        f"<b>{html.escape(user['name'])}</b>\n"
        f"Use /avatar to change your trainer!"
    )
    await update.message.reply_photo(photo=InputFile(image, filename="profile.png"), caption=caption, parse_mode=ParseMode.HTML)


def build_avatar_keyboard(index):
    total = len(TRAINER_AVATARS)
    nav = []
    if index > 0:
        nav.append(InlineKeyboardButton("⬅️ Back", callback_data=f"avatar:view:{index - 1}"))
    nav.append(InlineKeyboardButton(f"{index + 1}/{total}", callback_data="avatar:noop"))
    if index < total - 1:
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"avatar:view:{index + 1}"))
    set_row = [InlineKeyboardButton("✅ Set as Avatar", callback_data=f"avatar:set:{index}")]
    return InlineKeyboardMarkup([nav, set_row])


AVATAR_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PokeBotAvatarFetcher/1.0)"}


async def fetch_avatar_bytes(url):
    def _fetch():
        resp = requests.get(url, timeout=15, headers=AVATAR_HEADERS)
        resp.raise_for_status()
        return resp.content
    return await asyncio.to_thread(_fetch)


async def avatar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = ensure_started(update)
    user = get_user(user_id)
    current = user["avatar_index"] or 0
    trainer = TRAINER_AVATARS[current]
    try:
        content = await fetch_avatar_bytes(trainer["url"])
        photo_bytes = BytesIO(content)
        photo_bytes.seek(0)
        caption = (
            f"<b>Choose Your Trainer Avatar</b>\n\n"
            f"👤 <b>{trainer['name']}</b>  ({current + 1}/{len(TRAINER_AVATARS)})\n"
            f"Currently active avatar"
        )
        await update.message.reply_photo(
            photo=InputFile(photo_bytes, filename=f"trainer_{current}.png"),
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=build_avatar_keyboard(current),
        )
    except Exception as e:
        await update.message.reply_text(f"⚠️ Could not load avatar images right now. Try again later.\nError: {e}")


async def avatar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = ensure_started(update)
    parts = query.data.split(":")

    if parts[1] == "noop":
        return

    if parts[1] == "view":
        index = safe_int(parts[2], 0)
        index = max(0, min(index, len(TRAINER_AVATARS) - 1))
        trainer = TRAINER_AVATARS[index]
        user = get_user(user_id)
        current = user["avatar_index"] or 0
        active_label = " ✅ (current)" if index == current else ""
        try:
            content = await fetch_avatar_bytes(trainer["url"])
            photo_bytes = BytesIO(content)
            photo_bytes.seek(0)
            caption = (
                f"<b>Choose Your Trainer Avatar</b>\n\n"
                f"👤 <b>{trainer['name']}</b>{html.escape(active_label)}  ({index + 1}/{len(TRAINER_AVATARS)})"
            )
            await query.edit_message_media(
                media=InputMediaPhoto(
                    InputFile(photo_bytes, filename=f"trainer_{index}.png"),
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                ),
                reply_markup=build_avatar_keyboard(index),
            )
        except Exception:
            await query.answer("Could not load this avatar image.", show_alert=True)

    elif parts[1] == "set":
        index = safe_int(parts[2], 0)
        index = max(0, min(index, len(TRAINER_AVATARS) - 1))
        update_user(user_id, avatar_index=index)
        trainer = TRAINER_AVATARS[index]
        await query.answer(f"Avatar set to {trainer['name']}!", show_alert=True)
        try:
            content = await fetch_avatar_bytes(trainer["url"])
            photo_bytes = BytesIO(content)
            photo_bytes.seek(0)
            caption = (
                f"<b>Choose Your Trainer Avatar</b>\n\n"
                f"👤 <b>{trainer['name']}</b> ✅ (current)  ({index + 1}/{len(TRAINER_AVATARS)})"
            )
            await query.edit_message_media(
                media=InputMediaPhoto(
                    InputFile(photo_bytes, filename=f"trainer_{index}.png"),
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                ),
                reply_markup=build_avatar_keyboard(index),
            )
        except Exception:
            pass


async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_started(update)
    with db() as conn:
        coins = conn.execute("SELECT name, coins FROM users ORDER BY coins DESC LIMIT 10").fetchall()
        collectors = conn.execute("SELECT u.name, COUNT(p.id) AS total FROM users u LEFT JOIN caught_pokemon p ON p.user_id = u.user_id GROUP BY u.user_id ORDER BY total DESC LIMIT 10").fetchall()
        ivs = conn.execute("SELECT u.name, p.pokemon_name, (p.iv_hp+p.iv_atk+p.iv_def+p.iv_spa+p.iv_spd+p.iv_spe) AS iv FROM caught_pokemon p JOIN users u ON u.user_id = p.user_id ORDER BY iv DESC LIMIT 10").fetchall()
        wins_lb = conn.execute("SELECT name, wins FROM users ORDER BY wins DESC LIMIT 10").fetchall()
    lines = ["<b>Top Coins</b>"]
    lines.extend([f"{i}. {html.escape(r['name'])}: {r['coins']} PD" for i, r in enumerate(coins, 1)])
    lines.append("\n<b>Top Collectors</b>")
    lines.extend([f"{i}. {html.escape(r['name'])}: {r['total']} Pokémon" for i, r in enumerate(collectors, 1)])
    lines.append("\n<b>Top Battlers (Wins)</b>")
    lines.extend([f"{i}. {html.escape(r['name'])}: {r['wins']} wins" for i, r in enumerate(wins_lb, 1)])
    lines.append("\n<b>Highest IV Pokémon</b>")
    lines.extend([f"{i}. {html.escape(r['name'])}: {html.escape(r['pokemon_name'])} IV {r['iv']}/186" for i, r in enumerate(ivs, 1)])
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = ensure_started(update)
    sender = get_user(user_id)
    reply = update.message.reply_to_message

    if reply and reply.from_user and not reply.from_user.is_bot:
        target_id = reply.from_user.id
        target_name = reply.from_user.full_name or reply.from_user.first_name or str(target_id)
        amount = safe_int(context.args[0]) if context.args else None
        if not amount or amount <= 0:
            await update.message.reply_text(
                "💸 Reply to someone's message and use:\n<code>/gift &lt;amount&gt;</code>\nExample: /gift 100",
                parse_mode=ParseMode.HTML,
            )
            return
    elif context.args and len(context.args) >= 2:
        target_id = safe_int(context.args[0])
        amount = safe_int(context.args[1])
        if not target_id or not amount or amount <= 0:
            await update.message.reply_text(
                "💸 Usage:\n• Reply to someone's message: <code>/gift &lt;amount&gt;</code>\n• Or by ID: <code>/gift &lt;user_id&gt; &lt;amount&gt;</code>",
                parse_mode=ParseMode.HTML,
            )
            return
        target_tg = await context.bot.get_chat(target_id)
        target_name = target_tg.full_name or str(target_id)
    else:
        await update.message.reply_text(
            "💸 Usage:\n• Reply to someone's message: <code>/gift &lt;amount&gt;</code>\n• Or by ID: <code>/gift &lt;user_id&gt; &lt;amount&gt;</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    add_user(target_id, target_name)
    target = get_user(target_id)
    if not target:
        await update.message.reply_text("❌ That user has not started the bot yet.")
        return
    if target_id == user_id:
        await update.message.reply_text("❌ You cannot gift PD to yourself.")
        return
    if sender["coins"] < amount:
        await update.message.reply_text(f"❌ You don't have enough PD. You have <b>{sender['coins']} PD</b>.", parse_mode=ParseMode.HTML)
        return

    update_user(user_id, coins=sender["coins"] - amount)
    update_user(target_id, coins=target["coins"] + amount)

    sender_name = html.escape(update.effective_user.full_name or update.effective_user.first_name or str(user_id))
    await update.message.reply_text(
        f"✅ <b>{sender_name}</b> gifted <b>{amount} PD</b> to <b>{html.escape(target_name)}</b>!\n"
        f"💰 Your remaining PD: <b>{sender['coins'] - amount}</b>",
        parse_mode=ParseMode.HTML,
    )


async def trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = ensure_started(update)
    if len(context.args) < 3:
        await update.message.reply_text("Use: /trade target_user_id your_poke_id their_poke_id")
        return
    target = safe_int(context.args[0])
    mine = safe_int(context.args[1])
    theirs = safe_int(context.args[2])
    if not get_user(target):
        await update.message.reply_text("Target user must start the bot first.")
        return
    if not get_pokemon_row(user_id, mine):
        await update.message.reply_text("Your Pokémon ID not found.")
        return
    if not get_pokemon_row(target, theirs):
        await update.message.reply_text("Their Pokémon ID not found.")
        return
    with db() as conn:
        cur = conn.execute("INSERT INTO trade_requests (from_user_id, to_user_id, from_poke_id, to_poke_id) VALUES (?, ?, ?, ?)", (user_id, target, mine, theirs))
        request_id = cur.lastrowid
    await update.message.reply_text(f"Trade request #{request_id} created. Target user can accept with /trade_accept {request_id}.")


async def trade_accept(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = ensure_started(update)
    request_id = safe_int(context.args[0]) if context.args else None
    if not request_id:
        await update.message.reply_text("Use: /trade_accept request_id")
        return
    with db() as conn:
        req = conn.execute("SELECT * FROM trade_requests WHERE id = ? AND to_user_id = ? AND status = 'pending'", (request_id, user_id)).fetchone()
        if not req:
            await update.message.reply_text("Trade request not found.")
            return
        mine = conn.execute("SELECT * FROM caught_pokemon WHERE id = ? AND user_id = ?", (req["to_poke_id"], req["to_user_id"])).fetchone()
        theirs = conn.execute("SELECT * FROM caught_pokemon WHERE id = ? AND user_id = ?", (req["from_poke_id"], req["from_user_id"])).fetchone()
        if not mine or not theirs:
            await update.message.reply_text("Trade failed because one Pokémon is missing.")
            return
        conn.execute("UPDATE caught_pokemon SET user_id = ? WHERE id = ?", (req["to_user_id"], req["from_poke_id"]))
        conn.execute("UPDATE caught_pokemon SET user_id = ? WHERE id = ?", (req["from_user_id"], req["to_poke_id"]))
        conn.execute("UPDATE trade_requests SET status = 'accepted' WHERE id = ?", (request_id,))
    await update.message.reply_text(f"Trade #{request_id} completed.")


async def lore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_started(update)
    if not context.args:
        await update.message.reply_text(
            "<b>/lore</b> — look up details on any item or Pokémon.\n\n"
            "<b>Examples:</b>\n"
            "/lore Charizardite X\n"
            "/lore Rare Candy\n"
            "/lore Firium Z\n"
            "/lore Ditto",
            parse_mode=ParseMode.HTML,
        )
        return
    query_str = " ".join(context.args)
    name = query_str.title()
    title = f"{name}_(Pokémon)"
    try:
        params = {"action": "query", "format": "json", "prop": "extracts", "exintro": 1, "explaintext": 1, "titles": title}
        data = requests.get("https://bulbapedia.bulbagarden.net/w/api.php", params=params, timeout=20, headers={"User-Agent": "HexaTelegramBot/1.0"}).json()
        page = next(iter(data["query"]["pages"].values()))
        extract = page.get("extract", "").strip()
        if not extract or extract.startswith("may refer to") or len(extract) < 30:
            await update.message.reply_text(f"No lore found for <b>{html.escape(name)}</b>.", parse_mode=ParseMode.HTML)
            return
        await update.message.reply_text(f"<b>📖 {html.escape(name)}</b>\n\n{html.escape(extract[:1400])}", parse_mode=ParseMode.HTML)
    except Exception as exc:
        await update.message.reply_text(f"Could not fetch lore for <b>{html.escape(name)}</b>: {html.escape(str(exc))}", parse_mode=ParseMode.HTML)


async def tm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = ensure_started(update)
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Use: /tm <Pokémon ID> <move-name>\n"
            "Example: /tm 42 flamethrower\n\n"
            "You need a TM for that move in your inventory."
        )
        return
    caught_id = safe_int(context.args[0])
    move_name = "-".join(context.args[1:]).lower().strip()
    if not caught_id:
        await update.message.reply_text("First argument must be a Pokémon ID number.")
        return
    row = get_pokemon_row(user_id, caught_id)
    if not row:
        await update.message.reply_text("You don't own that Pokémon.")
        return
    tm_item_name = f"TM {move_name.replace('-', ' ')}"
    if get_item_qty(user_id, tm_item_name) <= 0:
        await update.message.reply_text(f"You don't have a {tm_item_name}. Check /inv for your TMs.")
        return
    info = poke_data.get_base_stats_types_sprites(row["pokemon_id"])
    learnable = poke_data.get_learnable_moves(row["pokemon_id"])
    if learnable and move_name not in learnable:
        move_display = move_name.replace("-", " ").title()
        await update.message.reply_text(
            f"{html.escape(display_name(row))} cannot learn {html.escape(move_display)}."
        )
        return
    current_moves = json.loads(row["moves_learned"])
    if move_name in current_moves:
        await update.message.reply_text(f"{html.escape(display_name(row))} already knows {move_name.replace('-', ' ').title()}!")
        return
    if len(current_moves) >= 4:
        current_moves[-1] = move_name
    else:
        current_moves.append(move_name)
    use_item(user_id, tm_item_name, 1)
    with db() as conn:
        conn.execute(
            "UPDATE caught_pokemon SET moves_learned = ? WHERE id = ? AND user_id = ?",
            (json.dumps(current_moves), caught_id, user_id)
        )
    move_display = move_name.replace("-", " ").title()
    moves_text = ", ".join(m.replace("-", " ").title() for m in current_moves)
    await update.message.reply_text(
        f"✅ {html.escape(display_name(row))} learned <b>{html.escape(move_display)}</b>!\n"
        f"Current moves: {html.escape(moves_text)}",
        parse_mode=ParseMode.HTML
    )


def build_app():
    if not BOT_TOKEN:
        raise RuntimeError("Set BOT_TOKEN before running this bot.")
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("open", open_menu))
    app.add_handler(CommandHandler("close", close_menu))
    app.add_handler(CommandHandler("hunt", hunt))
    app.add_handler(CommandHandler("daily", daily))
    app.add_handler(CommandHandler("referral", referral))
    app.add_handler(CommandHandler("safari", safari))
    app.add_handler(CommandHandler("enter", safari_enter))
    app.add_handler(CommandHandler("exit", safari_exit))
    app.add_handler(CommandHandler("team", team))
    app.add_handler(CommandHandler("inv", inv))
    app.add_handler(CommandHandler("inventory", inv))
    app.add_handler(CommandHandler("collection", collection))
    app.add_handler(CommandHandler("slot", slot))
    app.add_handler(CommandHandler("card", card))
    app.add_handler(CommandHandler("data", data_cmd))
    app.add_handler(CommandHandler("lore", lore))
    app.add_handler(CommandHandler("battle", battle))
    app.add_handler(CommandHandler("travel", travel))
    app.add_handler(CommandHandler("shop", shop))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("evolve", evolve))
    app.add_handler(CommandHandler("rename", rename))
    app.add_handler(CommandHandler("hatch", hatch))
    app.add_handler(CommandHandler("run", run_cmd))
    app.add_handler(CommandHandler("candy", candy))
    app.add_handler(CommandHandler("vitamin", vitamin))
    app.add_handler(CommandHandler("berry", berry))
    app.add_handler(CommandHandler("tm", tm))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("profial", profile))
    app.add_handler(CommandHandler("avatar", avatar))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("gift", gift))
    app.add_handler(CommandHandler("trade", trade))
    app.add_handler(CommandHandler("trade_accept", trade_accept))
    app.add_handler(CommandHandler("pokerandom", pokerandom))
    app.add_handler(CommandHandler("bordchast", bordchast))
    app.add_handler(CommandHandler("create", create_code))
    app.add_handler(CommandHandler("redeem", redeem_code))
    app.add_handler(CommandHandler("add", admin_add_poke))
    app.add_handler(CommandHandler("gyms", gyms))
    app.add_handler(ChatMemberHandler(track_group_membership, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(CallbackQueryHandler(open_menu_callback, pattern=r"^open_menu:"))
    app.add_handler(CallbackQueryHandler(card_pick_callback, pattern=r"^card_pick:"))
    app.add_handler(CallbackQueryHandler(starter_callback, pattern=r"^starter:"))
    app.add_handler(CallbackQueryHandler(cardview_callback, pattern=r"^cardview:"))
    app.add_handler(CallbackQueryHandler(collection_callback, pattern=r"^col:"))
    app.add_handler(CallbackQueryHandler(slot_callback, pattern=r"^slot:"))
    app.add_handler(CallbackQueryHandler(inv_callback, pattern=r"^inv:"))
    app.add_handler(CallbackQueryHandler(shop_callback, pattern=r"^shop:"))
    app.add_handler(CallbackQueryHandler(safari_zone_callback, pattern=r"^safari_zone:"))
    app.add_handler(CallbackQueryHandler(throw_callback, pattern=r"^throw:"))
    app.add_handler(CallbackQueryHandler(encounter_callback, pattern=r"^(catch|kill|run)$"))
    app.add_handler(CallbackQueryHandler(challenge_callback, pattern=r"^challenge:"))
    app.add_handler(CallbackQueryHandler(pvp_battle_callback, pattern=r"^pvp:"))
    app.add_handler(CallbackQueryHandler(travel_callback, pattern=r"^travel:"))
    app.add_handler(CallbackQueryHandler(team_callback, pattern=r"^team:"))
    app.add_handler(CallbackQueryHandler(avatar_callback, pattern=r"^avatar:"))
    app.add_handler(CallbackQueryHandler(candy_callback, pattern=r"^candy:"))
    app.add_handler(CallbackQueryHandler(vitamin_callback, pattern=r"^vitamin:"))
    app.add_handler(CallbackQueryHandler(berry_callback, pattern=r"^berry:"))
    return app


if __name__ == "__main__":
    application = build_app()
    print("Hexa-style Pokémon Telegram bot is running.")
    application.run_polling()
