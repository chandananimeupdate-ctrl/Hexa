import asyncio
import io
import logging
import os
import time
from collections import defaultdict

import aiohttp
import aiosqlite
import requests as req_lib
from PIL import Image, ImageDraw, ImageFont
from telegram import (
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Update,
    BotCommand,
)
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("8696513039:AAGc0XQ7lJ6quVvzHKKofVIHh_viXjxicJk")

# ── Database ──────────────────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "bot_data.db")


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS group_settings (
                chat_id INTEGER PRIMARY KEY,
                welcome_message TEXT DEFAULT 'Welcome to the group, {name}!',
                welcome_enabled INTEGER DEFAULT 1
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS banned_users (
                user_id INTEGER,
                chat_id INTEGER,
                banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, chat_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS message_counts (
                user_id    INTEGER,
                chat_id    INTEGER,
                username   TEXT,
                first_name TEXT,
                count      INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, chat_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS likes (
                liker_id    INTEGER,
                liked_id    INTEGER,
                chat_id     INTEGER,
                liked_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (liker_id, liked_id, chat_id)
            )
        """)
        await db.commit()


async def add_user(user_id: int, username: str, first_name: str, last_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        """, (user_id, username, first_name, last_name))
        await db.commit()


async def get_all_user_ids() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [r[0] for r in rows]


async def get_welcome_message(chat_id: int) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT welcome_message FROM group_settings WHERE chat_id = ?", (chat_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else "Welcome to the group, {name}! 🎉"


async def set_welcome_message(chat_id: int, message: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO group_settings (chat_id, welcome_message)
            VALUES (?, ?)
        """, (chat_id, message))
        await db.commit()


async def increment_message_count(user_id: int, chat_id: int, username: str, first_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO message_counts (user_id, chat_id, username, first_name, count)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(user_id, chat_id) DO UPDATE SET
                count      = count + 1,
                username   = excluded.username,
                first_name = excluded.first_name
        """, (user_id, chat_id, username, first_name))
        await db.commit()


async def get_leaderboard(chat_id: int, limit: int = 10) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT user_id, username, first_name, count
            FROM message_counts
            WHERE chat_id = ?
            ORDER BY count DESC
            LIMIT ?
        """, (chat_id, limit)) as cursor:
            rows = await cursor.fetchall()
            return [
                {"user_id": r[0], "username": r[1], "first_name": r[2], "count": r[3]}
                for r in rows
            ]


async def reset_leaderboard(chat_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM message_counts WHERE chat_id = ?", (chat_id,))
        await db.commit()


async def give_like(liker_id: int, liked_id: int, chat_id: int) -> bool:
    """Returns True if like was new, False if already liked today."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT liked_at FROM likes
            WHERE liker_id = ? AND liked_id = ? AND chat_id = ?
              AND DATE(liked_at) = DATE('now')
        """, (liker_id, liked_id, chat_id)) as cursor:
            row = await cursor.fetchone()
        if row:
            return False
        await db.execute("""
            INSERT OR IGNORE INTO likes (liker_id, liked_id, chat_id)
            VALUES (?, ?, ?)
        """, (liker_id, liked_id, chat_id))
        await db.commit()
        return True


async def get_like_count(user_id: int, chat_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT COUNT(*) FROM likes WHERE liked_id = ? AND chat_id = ?
        """, (user_id, chat_id)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


# ── Image generation ──────────────────────────────────────────────────────────
def get_font(size=18, bold=False):
    try:
        if bold:
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()


def download_image(url: str):
    try:
        resp = req_lib.get(url, timeout=10)
        if resp.status_code == 200:
            return Image.open(io.BytesIO(resp.content)).convert("RGBA")
    except Exception:
        pass
    return None


def create_type_chart_image(types: list) -> bytes:
    weaknesses = get_weaknesses(types)
    W, H = 600, 500
    img = Image.new("RGB", (W, H), color=(15, 20, 40))
    draw = ImageDraw.Draw(img)
    font_big = get_font(24, bold=True)
    font_med = get_font(17, bold=True)
    font_sm = get_font(15)
    type_str = " / ".join([t.title() for t in types])
    draw.text((20, 15), f"Type Chart: {type_str}", fill=(255, 230, 100), font=font_big)
    y = 60
    sections = [
        ("4x WEAK (Double Weakness):", weaknesses["double_weak"], (255, 80, 80)),
        ("2x WEAK:", weaknesses["weak"], (255, 160, 80)),
        ("IMMUNE (0x):", weaknesses["immune"], (100, 220, 100)),
        ("RESISTANT (0.5x):", weaknesses["resist"][:8], (100, 160, 255)),
    ]
    for title, items, color in sections:
        if not items:
            continue
        draw.text((20, y), title, fill=color, font=font_med)
        y += 25
        row_items = ["  ".join([f"{get_type_emoji(t)} {t.title()}" for t in items])]
        draw.text((30, y), row_items[0], fill=(220, 220, 220), font=font_sm)
        y += 30
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG", optimize=True)
    img_bytes.seek(0)
    return img_bytes.getvalue()


def create_leaderboard_image(entries: list, chat_title: str = "Group") -> bytes:
    W = 700
    ROW_H = 44
    HEADER = 90
    FOOTER = 30
    H = HEADER + len(entries) * ROW_H + FOOTER + 10
    BG = (28, 18, 18)
    HEADER_BG = (60, 15, 15)
    BAR_CLR = (180, 40, 40)
    BAR_ALT = (140, 30, 30)
    TEXT_W = (245, 235, 235)
    TEXT_DIM = (160, 140, 140)
    GOLD = (230, 180, 40)
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, 0), (W, HEADER)], fill=HEADER_BG)
    for off in range(0, W + H, 28):
        draw.line([(off, 0), (off - HEADER, HEADER)], fill=(70, 20, 20), width=14)
    font_title = get_font(32, bold=True)
    font_sub = get_font(13)
    font_rank = get_font(14, bold=True)
    font_name = get_font(15, bold=True)
    font_num = get_font(14)
    title = "LEADERBOARD"
    tw = draw.textlength(title, font=font_title)
    draw.text(((W - tw) // 2, 15), title, fill=(255, 255, 255), font=font_title)
    sub = chat_title[:40]
    sw = draw.textlength(sub, font=font_sub)
    draw.text(((W - sw) // 2, 62), sub, fill=TEXT_DIM, font=font_sub)
    cx, cy, cr = W - 55, H // 2 + 10, 90
    draw.ellipse([(cx - cr, cy - cr), (cx + cr, cy + cr)], fill=(38, 22, 22))
    draw.ellipse([(cx - cr, cy - cr), (cx + cr, cy + cr)], outline=(55, 30, 30), width=3)
    draw.rectangle([(cx - cr, cy - 5), (cx + cr, cy + 5)], fill=(45, 25, 25))
    draw.ellipse([(cx - 22, cy - 22), (cx + 22, cy + 22)], fill=(48, 28, 28), outline=(60, 35, 35), width=2)
    max_count = max((e["count"] for e in entries), default=1)
    BAR_LEFT = 160
    BAR_RIGHT = W - 110
    BAR_W = BAR_RIGHT - BAR_LEFT
    for i, entry in enumerate(entries):
        rank = i + 1
        y0 = HEADER + i * ROW_H
        y_mid = y0 + ROW_H // 2
        row_bg = (34, 20, 20) if i % 2 == 0 else (30, 17, 17)
        draw.rectangle([(0, y0), (W, y0 + ROW_H - 1)], fill=row_bg)
        rank_str = ["1st", "2nd", "3rd"][rank - 1] if rank <= 3 else f"#{rank}"
        rank_col = GOLD if rank <= 3 else TEXT_DIM
        draw.text((10, y_mid - 9), rank_str, fill=rank_col, font=font_rank)
        name = (entry.get("first_name") or entry.get("username") or "Unknown")[:18]
        draw.text((55, y_mid - 9), name, fill=TEXT_W, font=font_name)
        ratio = entry["count"] / max_count if max_count > 0 else 0
        bar_len = max(6, int(ratio * BAR_W))
        bar_col = BAR_CLR if i % 2 == 0 else BAR_ALT
        bar_y0 = y_mid - 10
        bar_y1 = y_mid + 10
        draw.rectangle([(BAR_LEFT, bar_y0), (BAR_LEFT + bar_len, bar_y1)], fill=bar_col)
        draw.rectangle([(BAR_LEFT, bar_y0), (BAR_LEFT + bar_len, bar_y0 + 3)], fill=(210, 60, 60))
        count_str = f"{entry['count']:,}"
        draw.text((BAR_LEFT + bar_len + 6, y_mid - 9), count_str, fill=TEXT_W, font=font_num)
    fy = H - FOOTER + 4
    draw.rectangle([(0, fy - 4), (W, H)], fill=(22, 14, 14))
    total = sum(e["count"] for e in entries)
    footer_txt = f"GreDex | PokeDataBot  •  Total messages: {total:,}"
    draw.text((14, fy), footer_txt, fill=TEXT_DIM, font=font_sub)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf.getvalue()


def get_shiny_url(pokemon_data: dict) -> str:
    official_shiny = (
        pokemon_data.get("sprites", {})
                    .get("other", {})
                    .get("official-artwork", {})
                    .get("front_shiny")
    )
    if official_shiny:
        return official_shiny
    return pokemon_data.get("sprites", {}).get("front_shiny")


# ── PokeAPI ────────────────────────────────────────────────────────────────────
POKEAPI_BASE = "https://pokeapi.co/api/v2"

TYPE_EMOJIS = {
    "fire": "🔥", "water": "💧", "grass": "🌿", "electric": "⚡",
    "ice": "❄️", "fighting": "🥊", "poison": "☠️", "ground": "🌍",
    "flying": "🦅", "psychic": "🔮", "bug": "🐛", "rock": "🪨",
    "ghost": "👻", "dragon": "🐉", "dark": "🌑", "steel": "⚙️",
    "fairy": "🧚", "normal": "⚪",
}

TYPE_CHART = {
    "normal":    {"weak": ["fighting"], "immune": ["ghost"], "resist": [""]},
    "fire":      {"weak": ["water","ground","rock"], "immune": [], "resist": ["fire","grass","ice","bug","steel","fairy"]},
    "water":     {"weak": ["electric","grass"], "immune": [], "resist": ["fire","water","ice","steel"]},
    "electric":  {"weak": ["ground"], "immune": [], "resist": ["electric","flying","steel"]},
    "grass":     {"weak": ["fire","ice","poison","flying","bug"], "immune": [], "resist": ["water","electric","grass","ground"]},
    "ice":       {"weak": ["fire","fighting","rock","steel"], "immune": [], "resist": ["ice"]},
    "fighting":  {"weak": ["flying","psychic","fairy"], "immune": [], "resist": ["bug","rock","dark"]},
    "poison":    {"weak": ["ground","psychic"], "immune": [], "resist": ["grass","fighting","poison","bug","fairy"]},
    "ground":    {"weak": ["water","grass","ice"], "immune": ["electric"], "resist": ["poison","rock"]},
    "flying":    {"weak": ["electric","ice","rock"], "immune": ["ground"], "resist": ["grass","fighting","bug"]},
    "psychic":   {"weak": ["bug","ghost","dark"], "immune": [], "resist": ["fighting","psychic"]},
    "bug":       {"weak": ["fire","flying","rock"], "immune": [], "resist": ["grass","fighting","ground"]},
    "rock":      {"weak": ["water","grass","fighting","ground","steel"], "immune": [], "resist": ["normal","fire","poison","flying"]},
    "ghost":     {"weak": ["ghost","dark"], "immune": ["normal","fighting"], "resist": ["poison","bug"]},
    "dragon":    {"weak": ["ice","dragon","fairy"], "immune": [], "resist": ["fire","water","electric","grass"]},
    "dark":      {"weak": ["fighting","bug","fairy"], "immune": ["psychic"], "resist": ["ghost","dark"]},
    "steel":     {"weak": ["fire","fighting","ground"], "immune": ["poison"], "resist": ["normal","grass","ice","flying","psychic","bug","rock","dragon","steel","fairy"]},
    "fairy":     {"weak": ["poison","steel"], "immune": ["dragon"], "resist": ["fighting","bug","dark"]},
}


async def fetch_json(session: aiohttp.ClientSession, url: str):
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                return await resp.json()
    except Exception:
        pass
    return None


async def get_pokemon(name: str):
    name = name.lower().strip().replace(" ", "-")
    async with aiohttp.ClientSession() as session:
        data = await fetch_json(session, f"{POKEAPI_BASE}/pokemon/{name}")
        if not data:
            return None
        species_data = await fetch_json(session, data["species"]["url"])
        return {"pokemon": data, "species": species_data}


async def get_move(name: str):
    name = name.lower().strip().replace(" ", "-")
    async with aiohttp.ClientSession() as session:
        return await fetch_json(session, f"{POKEAPI_BASE}/move/{name}")


async def get_evolution_chain_detailed(chain_url: str) -> dict:
    async with aiohttp.ClientSession() as session:
        data = await fetch_json(session, chain_url)
        if not data:
            return {"base": "", "steps": [], "branched": False}
        root = data.get("chain", {})
        base_name = root.get("species", {}).get("name", "")
        steps = _traverse_chain(root)
        branched = any(len(node.get("evolves_to", [])) > 1 for node in [root])
        return {"base": base_name, "steps": steps, "branched": branched}


def _format_evo_condition(detail: dict) -> str:
    trigger = detail.get("trigger", {}).get("name", "")
    parts = []
    if trigger == "level-up":
        lvl = detail.get("min_level")
        parts.append(f"Level up at level {lvl}" if lvl else "Level up")
        tod = detail.get("time_of_day", "")
        if tod:
            parts.append(f"during {tod}")
        happiness = detail.get("min_happiness")
        if happiness:
            parts.append(f"with {happiness}+ happiness")
        move_type = detail.get("known_move_type", {}) or {}
        if move_type.get("name"):
            parts.append(f"knowing a {move_type['name']}-type move")
        move = detail.get("known_move", {}) or {}
        if move.get("name"):
            parts.append(f"knowing {move['name'].replace('-', ' ').title()}")
        location = detail.get("location", {}) or {}
        if location.get("name"):
            parts.append(f"at {location['name'].replace('-', ' ').title()}")
    elif trigger == "use-item":
        item = detail.get("item", {}) or {}
        parts.append(f"Use {item.get('name','?').replace('-',' ').title()}")
    elif trigger == "trade":
        held = detail.get("held_item", {}) or {}
        parts.append(f"Trade holding {held['name'].replace('-',' ').title()}" if held.get("name") else "Trade")
    elif trigger == "shed":
        parts.append("Level up with empty party slot + Poké Ball")
    elif trigger == "spin":
        parts.append("Spin with item attached")
    elif trigger == "three-critical-hits":
        parts.append("Land 3 critical hits in one battle")
    elif trigger == "take-damage":
        parts.append("Travel after taking 49+ damage without fainting")
    else:
        parts.append(trigger.replace("-", " ").title())
    gender = detail.get("gender")
    if gender == 1:
        parts.append("(♀ only)")
    elif gender == 2:
        parts.append("(♂ only)")
    return ", ".join(parts) if parts else "?"


def _traverse_chain(node: dict, parent=None) -> list:
    steps = []
    species_name = node.get("species", {}).get("name", "")
    if parent and species_name:
        details = node.get("evolution_details", [])
        condition = _format_evo_condition(details[0]) if details else "?"
        steps.append({
            "from": parent,
            "to": species_name,
            "condition": condition,
            "level": (details[0].get("min_level") or 0) if details else 0,
        })
    for child in node.get("evolves_to", []):
        steps.extend(_traverse_chain(child, species_name))
    return steps


def get_alternate_forms(species_data: dict) -> list:
    varieties = species_data.get("varieties", [])
    base = species_data.get("name", "")
    forms = []
    for v in varieties:
        if not v.get("is_default"):
            pname = v.get("pokemon", {}).get("name", "")
            if pname:
                suffix = pname[len(base):].lstrip("-")
                label = suffix.replace("-", " ").title() if suffix else pname.title()
                forms.append({"name": pname, "label": label})
    return forms


def get_type_emoji(type_name: str) -> str:
    return TYPE_EMOJIS.get(type_name.lower(), "❓")


def get_weaknesses(types: list) -> dict:
    weaknesses = {}
    immunities = set()
    resistances = set()
    for t in types:
        t_lower = t.lower()
        if t_lower in TYPE_CHART:
            chart = TYPE_CHART[t_lower]
            for w in chart["weak"]:
                if w:
                    weaknesses[w] = weaknesses.get(w, 0) + 1
            for i in chart["immune"]:
                if i:
                    immunities.add(i)
            for r in chart["resist"]:
                if r:
                    resistances.add(r)
    effective_weak = []
    double_weak = []
    for w, count in weaknesses.items():
        if w not in immunities:
            if count >= 2:
                double_weak.append(w)
            elif w not in resistances:
                effective_weak.append(w)
    return {
        "weak": effective_weak,
        "double_weak": double_weak,
        "immune": list(immunities),
        "resist": list(resistances),
    }


def get_moves_by_method(pokemon_data: dict) -> dict:
    buckets = {"levelup": [], "machine": [], "tutor": [], "egg": []}
    seen = {k: set() for k in buckets}
    method_map = {"level-up": "levelup", "machine": "machine", "tutor": "tutor", "egg": "egg"}
    for move_entry in pokemon_data.get("moves", []):
        move_name = move_entry["move"]["name"]
        move_url = move_entry["move"]["url"]
        added_to = set()
        for vgd in move_entry.get("version_group_details", []):
            raw_method = vgd.get("move_learn_method", {}).get("name", "")
            bucket = method_map.get(raw_method)
            if bucket and bucket not in added_to and move_name not in seen[bucket]:
                seen[bucket].add(move_name)
                added_to.add(bucket)
                entry = {"name": move_name, "url": move_url}
                if bucket == "levelup":
                    entry["level"] = vgd.get("level_learned_at", 0)
                buckets[bucket].append(entry)
    buckets["levelup"].sort(key=lambda x: x.get("level", 0))
    return buckets


async def get_move_details_batch(move_entries: list, limit: int = 10) -> list:
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_json(session, e["url"]) for e in move_entries[:limit]]
        results = await asyncio.gather(*tasks)
        detailed = []
        for i, result in enumerate(results):
            if result:
                entry = move_entries[i]
                detailed.append({
                    "name": entry["name"],
                    "level": entry.get("level", 0),
                    "type": result.get("type", {}).get("name", "?"),
                    "damage_class": result.get("damage_class", {}).get("name", "?"),
                    "power": result.get("power") or 0,
                    "accuracy": result.get("accuracy") or 100,
                    "pp": result.get("pp", 0),
                })
        return detailed


# ── Competitive data ──────────────────────────────────────────────────────────
BEST_MOVESETS = {
    "charizard": {"moveset": ["flamethrower","air-slash","dragon-pulse","solar-beam"],"item": "Charizardite Y / Choice Specs","ability": "Blaze / Drought (Mega Y)","nature": "Timid / Modest","evs": "252 SpA / 4 SpD / 252 Spe","role": "Special Sweeper / Sun Setter"},
    "pikachu": {"moveset": ["thunderbolt","volt-tackle","iron-tail","quick-attack"],"item": "Light Ball","ability": "Static / Lightning Rod","nature": "Jolly / Timid","evs": "4 HP / 252 Atk / 252 Spe","role": "Fast Attacker"},
    "gengar": {"moveset": ["shadow-ball","sludge-wave","focus-blast","nasty-plot"],"item": "Choice Specs / Life Orb","ability": "Cursed Body","nature": "Timid","evs": "252 SpA / 4 SpD / 252 Spe","role": "Special Sweeper"},
    "garchomp": {"moveset": ["earthquake","dragon-claw","stone-edge","swords-dance"],"item": "Rocky Helmet / Choice Scarf","ability": "Rough Skin","nature": "Jolly","evs": "252 Atk / 4 SpD / 252 Spe","role": "Physical Sweeper / Wallbreaker"},
    "lucario": {"moveset": ["close-combat","bullet-punch","extreme-speed","swords-dance"],"item": "Life Orb","ability": "Justified / Inner Focus","nature": "Jolly / Adamant","evs": "252 Atk / 4 SpD / 252 Spe","role": "Physical Sweeper"},
}

BEST_NATURES = {
    "charizard": ["Timid (+Spe -Atk) — Best for Special sets","Modest (+SpA -Atk) — Max damage Special","Jolly (+Spe -SpA) — Physical sets"],
    "pikachu": ["Jolly (+Spe -SpA) — Physical sets","Timid (+Spe -Atk) — Special sets","Hasty (+Spe -Def) — Mixed"],
    "gengar": ["Timid (+Spe -Atk) — Outspeed threats","Modest (+SpA -Atk) — Max power"],
    "garchomp": ["Jolly (+Spe -SpA) — Outspeeds max speed","Adamant (+Atk -SpA) — Max damage"],
    "lucario": ["Jolly (+Spe -SpA) — Speed priority","Adamant (+Atk -SpA) — Max physical damage","Naive (+Spe -SpD) — Mixed Attacker"],
}

BEST_EVS = {
    "charizard": {"Special Sweeper": {"HP": 0,"Atk": 0,"Def": 4,"SpA": 252,"SpD": 0,"Spe": 252,"note": "Max speed and special attack"},"Bulky Attacker": {"HP": 80,"Atk": 0,"Def": 0,"SpA": 252,"SpD": 0,"Spe": 176,"note": "Tanky with power"},"Physical Sweeper": {"HP": 0,"Atk": 252,"Def": 4,"SpA": 0,"SpD": 0,"Spe": 252,"note": "Full physical attack"}},
    "pikachu": {"Fast Attacker": {"HP": 4,"Atk": 252,"Def": 0,"SpA": 0,"SpD": 0,"Spe": 252,"note": "Max attack and speed"}},
    "gengar": {"Special Sweeper": {"HP": 0,"Atk": 0,"Def": 4,"SpA": 252,"SpD": 0,"Spe": 252,"note": "Max speed and SpA"}},
    "garchomp": {"Physical Sweeper": {"HP": 0,"Atk": 252,"Def": 4,"SpA": 0,"SpD": 0,"Spe": 252,"note": "Max attack and speed"},"Bulky Physical": {"HP": 68,"Atk": 252,"Def": 0,"SpA": 0,"SpD": 0,"Spe": 188,"note": "Bulky sweeper"}},
    "lucario": {"Physical Sweeper": {"HP": 0,"Atk": 252,"Def": 4,"SpA": 0,"SpD": 0,"Spe": 252,"note": "Max attack and speed"},"Mixed Attacker": {"HP": 0,"Atk": 128,"Def": 0,"SpA": 128,"SpD": 4,"Spe": 248,"note": "Mixed offense"}},
}

NATURE_DATA = {
    "hardy": {"boost": None, "reduce": None, "desc": "Neutral nature, no stat change"},
    "lonely": {"boost": "Attack", "reduce": "Defense", "desc": "+Atk / -Def"},
    "brave": {"boost": "Attack", "reduce": "Speed", "desc": "+Atk / -Spe"},
    "adamant": {"boost": "Attack", "reduce": "Sp. Atk", "desc": "+Atk / -SpA"},
    "naughty": {"boost": "Attack", "reduce": "Sp. Def", "desc": "+Atk / -SpD"},
    "bold": {"boost": "Defense", "reduce": "Attack", "desc": "+Def / -Atk"},
    "docile": {"boost": None, "reduce": None, "desc": "Neutral nature, no stat change"},
    "relaxed": {"boost": "Defense", "reduce": "Speed", "desc": "+Def / -Spe"},
    "impish": {"boost": "Defense", "reduce": "Sp. Atk", "desc": "+Def / -SpA"},
    "lax": {"boost": "Defense", "reduce": "Sp. Def", "desc": "+Def / -SpD"},
    "timid": {"boost": "Speed", "reduce": "Attack", "desc": "+Spe / -Atk"},
    "hasty": {"boost": "Speed", "reduce": "Defense", "desc": "+Spe / -Def"},
    "serious": {"boost": None, "reduce": None, "desc": "Neutral nature, no stat change"},
    "jolly": {"boost": "Speed", "reduce": "Sp. Atk", "desc": "+Spe / -SpA"},
    "naive": {"boost": "Speed", "reduce": "Sp. Def", "desc": "+Spe / -SpD"},
    "modest": {"boost": "Sp. Atk", "reduce": "Attack", "desc": "+SpA / -Atk"},
    "mild": {"boost": "Sp. Atk", "reduce": "Defense", "desc": "+SpA / -Def"},
    "quiet": {"boost": "Sp. Atk", "reduce": "Speed", "desc": "+SpA / -Spe"},
    "bashful": {"boost": None, "reduce": None, "desc": "Neutral nature, no stat change"},
    "rash": {"boost": "Sp. Atk", "reduce": "Sp. Def", "desc": "+SpA / -SpD"},
    "calm": {"boost": "Sp. Def", "reduce": "Attack", "desc": "+SpD / -Atk"},
    "gentle": {"boost": "Sp. Def", "reduce": "Defense", "desc": "+SpD / -Def"},
    "sassy": {"boost": "Sp. Def", "reduce": "Speed", "desc": "+SpD / -Spe"},
    "careful": {"boost": "Sp. Def", "reduce": "Sp. Atk", "desc": "+SpD / -SpA"},
    "quirky": {"boost": None, "reduce": None, "desc": "Neutral nature, no stat change"},
}


# ── Anti-flood & message dedup state ──────────────────────────────────────────
flood_log: dict = defaultdict(list)
last_text: dict = {}
muted_until: dict = {}

FLOOD_WINDOW = 30
FLOOD_LIMIT = 8
MUTE_DURATION = 120

ADMIN_ID = 6671520580


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


async def check_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if user.id == ADMIN_ID:
        return True
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, user.id)
        return member.status in ["administrator", "creator"]
    except Exception:
        return False


# ── Handlers ──────────────────────────────────────────────────────────────────
def build_data_text(poke: dict, species: dict) -> str:
    name = poke["name"].title()
    poke_id = poke["id"]
    types = [t["type"]["name"] for t in poke.get("types", [])]
    abilities = [a["ability"]["name"].replace("-", " ").title() for a in poke.get("abilities", []) if not a["is_hidden"]]
    hidden = next((a["ability"]["name"].replace("-", " ").title() for a in poke.get("abilities", []) if a["is_hidden"]), None)
    stats = {s["stat"]["name"]: s["base_stat"] for s in poke.get("stats", [])}
    catch_rate = species.get("capture_rate", 0) if species else 0
    catch_pct = round((catch_rate / 255) * 100, 2)
    region_gen = ""
    if species:
        raw = species.get("generation", {}).get("name", "")
        region_gen = raw.replace("generation-", "").upper()
    ev_yield = []
    for s in poke.get("stats", []):
        if s["effort"] > 0:
            sn = s["stat"]["name"].replace("special-attack", "Sp.Atk").replace("special-defense", "Sp.Def")
            ev_yield.append(f"{sn.title()} +{s['effort']}")
    type_str = " / ".join([f"{t.title()}{get_type_emoji(t)}" for t in types])

    def stat_bar(val):
        filled = int((val / 255) * 10)
        return "█" * filled + "░" * (10 - filled)

    def stat_range(base, key):
        if key == "hp":
            lo, hi = base * 2 + 110, base * 2 + 204
        else:
            lo = int((base * 2 + 5) * 0.9)
            hi = int((base * 2 + 5) * 1.1)
        return lo, hi

    stat_keys = ["hp", "attack", "defense", "special-attack", "special-defense", "speed"]
    stat_labels = {"hp": "HP", "attack": "Atk", "defense": "Def", "special-attack": "SpA", "special-defense": "SpD", "speed": "Spe"}
    stat_lines = []
    for key in stat_keys:
        val = stats.get(key, 0)
        lo, hi = stat_range(val, key)
        bar = stat_bar(val)
        lbl = stat_labels[key]
        stat_lines.append(f"`{lbl:3}` `{val:3}` `{bar}` `({lo}-{hi})`")
    total = sum(stats.values())
    text = (
        f"*{name}* `#{poke_id}`\n"
        f"{'─' * 30}\n"
        f"○ REGION    `: {region_gen}`\n"
        f"● TYPES     `: {type_str}`\n"
        f"● CATCH RATE`: {catch_rate} ({catch_pct}%)`\n"
        f"● DEX ID    `: #{poke_id}`\n"
        f"● ABILITIES `: {', '.join(abilities)}`\n"
    )
    if hidden:
        text += f"○ HIDDEN ABL`: {hidden}`\n"
    if ev_yield:
        text += f"● EV YIELD  `: {', '.join(ev_yield)}`\n"
    text += f"\n`{'─' * 28}`\n*BASE STATS*\n"
    for line in stat_lines:
        text += line + "\n"
    text += f"`{'─' * 28}`\n`{'TOTAL':>7} {total}`"
    return text


def main_keyboard(name: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗡 Moves", callback_data=f"moves_{name}_lvl_0"),
         InlineKeyboardButton("⚠️ Weakness", callback_data=f"weakness_{name}")],
        [InlineKeyboardButton("🔄 Evolutions", callback_data=f"evos_{name}"),
         InlineKeyboardButton("✨ Shiny", callback_data=f"shiny_{name}")],
    ])


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await add_user(user.id, user.username, user.first_name, user.last_name or "")
    welcome_text = (
        "🎮 *Pokémon Data Bot*\n\n"
        "Your ultimate Pokémon companion!\n\n"
        "📊 `/data charizard` — Full info + stats\n"
        "🗡 `/moveset charizard` — Best moveset\n"
        "🌿 `/bestnat charizard` — Best natures\n"
        "🔥 `/thype fire` — Type chart\n"
        "⚠️ `/weakness charizard` — Weaknesses\n"
        "📈 `/evsguid charizard` — EV spread\n"
        "🔍 Type any move name (e.g. `ice fang`)\n"
        "🌀 Type any nature (e.g. `timid`)\n\n"
        "👮 *Admin:* `/usertag` `/pin` `/ban` `/setwelcome`\n"
        "❤️ *Social:* `/like` — Like a user!"
    )
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("📊 Try Charizard", callback_data="demo_charizard"),
        InlineKeyboardButton("⚡ Type Chart", callback_data="demo_type"),
    ]])
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 *Commands*\n\n"
        "`/data <pokemon>` — Info card + stats\n"
        "`/moveset <pokemon>` — Competitive moveset\n"
        "`/bestnat <pokemon>` — Best natures\n"
        "`/thype <type>` — Type advantage chart\n"
        "`/weakness <pokemon>` — Weakness list\n"
        "`/evsguid <pokemon>` — EV build guide\n\n"
        "📊 *Leaderboard:*\n"
        "`/leaderboard` or `/lb` — Top chatters\n"
        "`/resetlb` — Reset leaderboard (admin)\n\n"
        "❤️ *Social:*\n"
        "`/like` — Reply to a user to like them\n\n"
        "🔍 Just type a move or nature name!\n\n"
        "👮 *Admin only:*\n"
        "`/usertag` `/pin` `/ban` `/unban` `/mute` `/setwelcome`\n\n"
        "📣 *Owner only:*\n"
        "`/broadcast <message>` — Send message to all users"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: `/data charizard`", parse_mode=ParseMode.MARKDOWN)
        return
    name = " ".join(context.args).lower().strip()
    msg = await update.message.reply_text(f"🔍 Looking up *{name.title()}*…", parse_mode=ParseMode.MARKDOWN)
    result = await get_pokemon(name)
    if not result:
        await msg.edit_text(f"❌ *{name.title()}* not found. Check the spelling.", parse_mode=ParseMode.MARKDOWN)
        return
    poke = result["pokemon"]
    species = result["species"]
    text = build_data_text(poke, species)
    sprite_url = (
        poke.get("sprites", {}).get("other", {}).get("official-artwork", {}).get("front_default")
        or poke.get("sprites", {}).get("front_default")
    )
    await msg.delete()
    if sprite_url:
        try:
            img = req_lib.get(sprite_url, timeout=10)
            if img.status_code == 200:
                await update.message.reply_photo(
                    photo=io.BytesIO(img.content),
                    caption=text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=main_keyboard(name),
                )
                return
        except Exception:
            pass
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=main_keyboard(name))


async def _edit(query, text: str, keyboard):
    try:
        if query.message.photo:
            await query.edit_message_caption(
                caption=text[:1024],
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard,
            )
        else:
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    except Exception as e:
        await query.answer(f"Error: {e}", show_alert=True)


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("moves_"):
        parts = data.split("_")
        poke_name = parts[1]
        method = parts[2] if len(parts) > 3 else "lvl"
        page = int(parts[-1]) if len(parts) > 2 else 0
        await send_moves(query, poke_name, method, page)
    elif data.startswith("weakness_"):
        await send_weakness_inline(query, data[len("weakness_"):])
    elif data.startswith("evos_"):
        await send_evolutions(query, data[len("evos_"):])
    elif data.startswith("formdata_"):
        payload = data[len("formdata_"):]
        idx = payload.index("_")
        await send_form_data(query, payload[:idx], payload[idx+1:])
    elif data.startswith("shiny_"):
        await send_shiny(query, data[len("shiny_"):])
    elif data.startswith("backinfo_"):
        await back_to_info(query, data[len("backinfo_"):])
    elif data.startswith("typechart_"):
        t = data[len("typechart_"):]
        await send_typechart_inline(query, [t])
    elif data == "demo_charizard":
        await query.message.reply_text("Try: `/data charizard`", parse_mode=ParseMode.MARKDOWN)
    elif data == "demo_type":
        await query.message.reply_text("Try: `/thype fire`", parse_mode=ParseMode.MARKDOWN)


async def back_to_info(query, name: str):
    result = await get_pokemon(name)
    if not result:
        await query.answer("Not found!", show_alert=True)
        return
    poke = result["pokemon"]
    species = result["species"]
    text = build_data_text(poke, species)
    sprite_url = (
        poke.get("sprites", {}).get("other", {}).get("official-artwork", {}).get("front_default")
        or poke.get("sprites", {}).get("front_default")
    )
    try:
        if query.message.photo and sprite_url:
            img = req_lib.get(sprite_url, timeout=10)
            if img.status_code == 200:
                await query.edit_message_media(
                    media=InputMediaPhoto(media=io.BytesIO(img.content), caption=text, parse_mode=ParseMode.MARKDOWN)
                )
                await query.edit_message_reply_markup(reply_markup=main_keyboard(name))
                return
        if query.message.photo:
            await query.edit_message_caption(caption=text, parse_mode=ParseMode.MARKDOWN, reply_markup=main_keyboard(name))
            return
    except Exception:
        pass
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=main_keyboard(name))


METHOD_LABELS = {"lvl": "📈 Level Up", "tm": "💿 TM/Machine", "tutor": "🎓 Tutor", "egg": "🥚 Egg Moves"}
METHOD_KEYS = {"lvl": "levelup", "tm": "machine", "tutor": "tutor", "egg": "egg"}


async def send_moves(query, name: str, method: str, page: int):
    result = await get_pokemon(name)
    if not result:
        await query.answer("Pokémon not found!", show_alert=True)
        return
    poke = result["pokemon"]
    all_moves = get_moves_by_method(poke)
    bucket_key = METHOD_KEYS.get(method, "levelup")
    move_list = all_moves.get(bucket_key, [])
    PER_PAGE = 8
    total_pages = max(1, (len(move_list) + PER_PAGE - 1) // PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    page_moves = move_list[page * PER_PAGE: (page + 1) * PER_PAGE]
    detailed = await get_move_details_batch(page_moves, limit=PER_PAGE)
    label = METHOD_LABELS.get(method, "Moves")
    lines = [f"🗡 *{name.title()} — {label}*\n`{len(move_list)} moves  •  Page {page+1}/{total_pages}`\n"]
    if not detailed:
        lines.append("_No moves in this category._")
    else:
        for i, move in enumerate(detailed, start=page * PER_PAGE + 1):
            t = move["type"]
            emoji = get_type_emoji(t)
            dc = move["damage_class"]
            pwr = move["power"] if move["power"] else "—"
            acc = f"{move['accuracy']}%" if move["accuracy"] else "—"
            if method == "lvl":
                meta = f"Lv.{move.get('level', 0)} | Pwr:{pwr} | Acc:{acc} | {dc.title()}"
            else:
                meta = f"Pwr:{pwr} | Acc:{acc} | {dc.title()}"
            lines.append(f"*{i}. {move['name'].replace('-',' ').title()}* {emoji}\n   `{meta}`")
    text = "\n".join(lines)
    tab_row = [
        InlineKeyboardButton(
            f"{'▸ ' if m == method else ''}{METHOD_LABELS[m].split()[0]}",
            callback_data=f"moves_{name}_{m}_0"
        )
        for m in ["lvl", "tm", "tutor", "egg"]
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"moves_{name}_{method}_{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data=f"moves_{name}_{method}_{page}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"moves_{name}_{method}_{page+1}"))
    rows = [tab_row]
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data=f"backinfo_{name}")])
    await _edit(query, text, InlineKeyboardMarkup(rows))


async def send_weakness_inline(query, name: str):
    result = await get_pokemon(name)
    if not result:
        await query.answer("Pokémon not found!", show_alert=True)
        return
    poke = result["pokemon"]
    types = [t["type"]["name"] for t in poke.get("types", [])]
    w = get_weaknesses(types)
    type_str = " / ".join([f"{t.title()}{get_type_emoji(t)}" for t in types])
    lines = [f"⚠️ *{name.title()} — Weaknesses*\n`Types: {type_str}`\n"]
    if w["double_weak"]:
        items = "  ".join([f"{get_type_emoji(t)} {t.title()}" for t in w["double_weak"]])
        lines.append(f"🔴 *4× Weak:*\n`{items}`")
    if w["weak"]:
        items = "  ".join([f"{get_type_emoji(t)} {t.title()}" for t in w["weak"]])
        lines.append(f"🟠 *2× Weak:*\n`{items}`")
    if w["immune"]:
        items = "  ".join([f"{get_type_emoji(t)} {t.title()}" for t in w["immune"]])
        lines.append(f"🟢 *Immune:*\n`{items}`")
    if w["resist"]:
        items = "  ".join([f"{get_type_emoji(t)} {t.title()}" for t in w["resist"][:10]])
        lines.append(f"🔵 *Resistant:*\n`{items}`")
    text = "\n".join(lines)
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=f"backinfo_{name}")]])
    await _edit(query, text, keyboard)


FORM_EMOJIS = {
    "mega": "🔮", "mega-x": "🔵", "mega-y": "🔴", "gmax": "⚡",
    "alola": "🌺", "alolan": "🌺", "galar": "⚔️", "galarian": "⚔️",
    "hisui": "🏔️", "hisuian": "🏔️", "paldea": "🌊", "paldean": "🌊",
}


def _form_emoji(label: str) -> str:
    key = label.lower().replace(" ", "-")
    for k, v in FORM_EMOJIS.items():
        if k in key:
            return v
    return "✨"


async def send_evolutions(query, name: str):
    result = await get_pokemon(name)
    if not result:
        await query.answer("Not found!", show_alert=True)
        return
    species = result.get("species") or {}
    chain_url = species.get("evolution_chain", {}).get("url")
    lines = [f"🔄 *Evolutions for {name.title()}*\n"]
    button_rows = []
    if chain_url:
        chain_data = await get_evolution_chain_detailed(chain_url)
        steps = chain_data.get("steps", [])
        if not steps:
            lines.append("_This Pokémon does not evolve._\n")
        else:
            for step in steps:
                frm = step["from"].replace("-", " ").title()
                to = step["to"].replace("-", " ").title()
                cond = step["condition"]
                lvl = step.get("level", 0)
                lines.append(f"💠 *{frm}* → *{to}*")
                lines.append(f"   _Method: {cond}, Level {lvl}_\n")
            all_members = [chain_data["base"]] + [s["to"] for s in steps]
            seen = []
            for m in all_members:
                if m not in seen:
                    seen.append(m)
            evo_buttons = [
                InlineKeyboardButton(m.replace("-", " ").title(), callback_data=f"formdata_{name}_{m}")
                for m in seen
            ]
            for i in range(0, len(evo_buttons), 2):
                button_rows.append(evo_buttons[i:i+2])
    else:
        lines.append("_No evolution data available._\n")
    forms = get_alternate_forms(species)
    if forms:
        lines.append("*Alternate Forms:*")
        for f in forms:
            emoji = _form_emoji(f["label"])
            lines.append(f"{emoji} {name.title()} {f['label']}")
        lines.append("")
        form_buttons = [
            InlineKeyboardButton(f"{_form_emoji(f['label'])} {f['label']}", callback_data=f"formdata_{name}_{f['name']}")
            for f in forms
        ]
        for i in range(0, len(form_buttons), 2):
            button_rows.append(form_buttons[i:i+2])
    text = "\n".join(lines)
    button_rows.append([InlineKeyboardButton("⬅️ Back to Info", callback_data=f"backinfo_{name}")])
    await _edit(query, text, InlineKeyboardMarkup(button_rows))


async def send_form_data(query, base_name: str, form_name: str):
    result = await get_pokemon(form_name)
    if not result:
        await query.answer(f"No data for {form_name}!", show_alert=True)
        return
    poke = result["pokemon"]
    species = result.get("species") or {}
    text = build_data_text(poke, species)
    sprite_url = (
        poke.get("sprites", {}).get("other", {}).get("official-artwork", {}).get("front_default")
        or poke.get("sprites", {}).get("front_default")
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗡 Moves", callback_data=f"moves_{form_name}_lvl_0"),
         InlineKeyboardButton("⚠️ Weakness", callback_data=f"weakness_{form_name}")],
        [InlineKeyboardButton("✨ Shiny", callback_data=f"shiny_{form_name}"),
         InlineKeyboardButton("⬅️ Back", callback_data=f"evos_{base_name}")],
    ])
    if sprite_url:
        try:
            img = req_lib.get(sprite_url, timeout=10)
            if img.status_code == 200:
                await query.edit_message_media(
                    media=InputMediaPhoto(media=io.BytesIO(img.content), caption=text[:1024], parse_mode=ParseMode.MARKDOWN)
                )
                await query.edit_message_reply_markup(reply_markup=keyboard)
                return
        except Exception:
            pass
    await _edit(query, text, keyboard)


async def send_shiny(query, name: str):
    result = await get_pokemon(name)
    if not result:
        await query.answer("Not found!", show_alert=True)
        return
    poke = result["pokemon"]
    shiny_url = get_shiny_url(poke)
    if not shiny_url:
        await query.answer("No shiny sprite available!", show_alert=True)
        return
    caption = f"✨ *{name.title()} — Shiny Form*\n_Tap Back to return to the full info card._"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=f"backinfo_{name}")]])
    try:
        img_data = req_lib.get(shiny_url, timeout=8)
        if img_data.status_code == 200:
            await query.edit_message_media(
                media=InputMediaPhoto(media=io.BytesIO(img_data.content), caption=caption, parse_mode=ParseMode.MARKDOWN)
            )
            await query.edit_message_reply_markup(reply_markup=keyboard)
            return
    except Exception:
        pass
    await _edit(query, caption, keyboard)


async def send_typechart_inline(query, types: list):
    valid_types = ["normal","fire","water","electric","grass","ice","fighting","poison","ground",
                   "flying","psychic","bug","rock","ghost","dragon","dark","steel","fairy"]
    try:
        img_bytes = create_type_chart_image(types)
        w = get_weaknesses(types)
        type_str = " / ".join([f"{t.title()}{get_type_emoji(t)}" for t in types])
        caption = f"🔥 *Type Chart: {type_str}*\n\n"
        if w["double_weak"]:
            caption += "🔴 *4× Weak:* " + " ".join([f"{get_type_emoji(t)}{t.title()}" for t in w["double_weak"]]) + "\n"
        if w["weak"]:
            caption += "🟠 *2× Weak:* " + " ".join([f"{get_type_emoji(t)}{t.title()}" for t in w["weak"]]) + "\n"
        if w["immune"]:
            caption += "🟢 *Immune:* " + " ".join([f"{get_type_emoji(t)}{t.title()}" for t in w["immune"]]) + "\n"
        if w["resist"]:
            caption += "🔵 *Resist:* " + " ".join([f"{get_type_emoji(t)}{t.title()}" for t in w["resist"][:8]])
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{get_type_emoji(t)}{t.title()}", callback_data=f"typechart_{t}") for t in valid_types[:6]],
            [InlineKeyboardButton(f"{get_type_emoji(t)}{t.title()}", callback_data=f"typechart_{t}") for t in valid_types[6:12]],
            [InlineKeyboardButton(f"{get_type_emoji(t)}{t.title()}", callback_data=f"typechart_{t}") for t in valid_types[12:]],
        ])
        await query.edit_message_media(
            media=InputMediaPhoto(media=io.BytesIO(img_bytes), caption=caption, parse_mode=ParseMode.MARKDOWN)
        )
        await query.edit_message_reply_markup(reply_markup=keyboard)
    except Exception as e:
        await query.answer(f"Error: {e}", show_alert=True)


async def moveset_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: `/moveset charizard`", parse_mode=ParseMode.MARKDOWN)
        return
    name = " ".join(context.args).lower().strip()
    moveset_data = BEST_MOVESETS.get(name)
    if not moveset_data:
        result = await get_pokemon(name)
        if not result:
            await update.message.reply_text(f"❌ *{name.title()}* not found!", parse_mode=ParseMode.MARKDOWN)
            return
        poke = result["pokemon"]
        stats = {s["stat"]["name"]: s["base_stat"] for s in poke.get("stats", [])}
        spa = stats.get("special-attack", 0)
        atk = stats.get("attack", 0)
        if spa > atk:
            role, nature, evs = "Special Sweeper", "Timid / Modest", "252 SpA / 4 SpD / 252 Spe"
        else:
            role, nature, evs = "Physical Sweeper", "Jolly / Adamant", "252 Atk / 4 SpD / 252 Spe"
        text = (
            f"⚔️ *{name.title()} — Recommended Moveset*\n\n"
            f"`Role   :` {role}\n"
            f"`Nature :` {nature}\n"
            f"`EVs    :` {evs}\n"
            f"`Item   :` Life Orb / Choice Specs\n"
        )
    else:
        moves = "\n".join([f"  `•` {m.replace('-', ' ').title()}" for m in moveset_data["moveset"]])
        text = (
            f"⚔️ *{name.title()} — Best Competitive Moveset*\n\n"
            f"`Role    :` {moveset_data['role']}\n"
            f"`Item    :` {moveset_data['item']}\n"
            f"`Ability :` {moveset_data['ability']}\n"
            f"`Nature  :` {moveset_data['nature']}\n"
            f"`EVs     :` {moveset_data['evs']}\n\n"
            f"🗡 *Moves:*\n{moves}"
        )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def bestnat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: `/bestnat charizard`", parse_mode=ParseMode.MARKDOWN)
        return
    name = " ".join(context.args).lower().strip()
    natures = BEST_NATURES.get(name)
    if not natures:
        result = await get_pokemon(name)
        if not result:
            await update.message.reply_text(f"❌ *{name.title()}* not found!", parse_mode=ParseMode.MARKDOWN)
            return
        poke = result["pokemon"]
        stats = {s["stat"]["name"]: s["base_stat"] for s in poke.get("stats", [])}
        if stats.get("special-attack", 0) > stats.get("attack", 0):
            natures = ["Timid (+Spe -Atk) — Speed priority", "Modest (+SpA -Atk) — Max damage"]
        else:
            natures = ["Jolly (+Spe -SpA) — Speed priority", "Adamant (+Atk -SpA) — Max damage"]
    nat_list = "\n".join([f"  🌿 `{n}`" for n in natures])
    await update.message.reply_text(
        f"🌿 *Best Natures for {name.title()}*\n\n{nat_list}",
        parse_mode=ParseMode.MARKDOWN
    )


async def thype_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    valid_types = ["normal","fire","water","electric","grass","ice","fighting","poison","ground",
                   "flying","psychic","bug","rock","ghost","dragon","dark","steel","fairy"]
    if not context.args:
        await update.message.reply_text(
            "Usage: `/thype fire` or `/thype fire water`\n\n"
            f"Valid types: {', '.join(valid_types)}",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    types = [arg.lower() for arg in context.args[:2]]
    for t in types:
        if t not in valid_types:
            await update.message.reply_text(f"❌ Unknown type: *{t}*", parse_mode=ParseMode.MARKDOWN)
            return
    msg = await update.message.reply_text("🔄 Building type chart…")
    try:
        img_bytes = create_type_chart_image(types)
        w = get_weaknesses(types)
        type_str = " / ".join([f"{t.title()}{get_type_emoji(t)}" for t in types])
        caption = f"🔥 *Type Chart: {type_str}*\n\n"
        if w["double_weak"]:
            caption += "🔴 *4× Weak:* " + " ".join([f"{get_type_emoji(t)}{t.title()}" for t in w["double_weak"]]) + "\n"
        if w["weak"]:
            caption += "🟠 *2× Weak:* " + " ".join([f"{get_type_emoji(t)}{t.title()}" for t in w["weak"]]) + "\n"
        if w["immune"]:
            caption += "🟢 *Immune:* " + " ".join([f"{get_type_emoji(t)}{t.title()}" for t in w["immune"]]) + "\n"
        if w["resist"]:
            caption += "🔵 *Resist:* " + " ".join([f"{get_type_emoji(t)}{t.title()}" for t in w["resist"][:8]])
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{get_type_emoji(t)}{t.title()}", callback_data=f"typechart_{t}") for t in valid_types[:6]],
            [InlineKeyboardButton(f"{get_type_emoji(t)}{t.title()}", callback_data=f"typechart_{t}") for t in valid_types[6:12]],
            [InlineKeyboardButton(f"{get_type_emoji(t)}{t.title()}", callback_data=f"typechart_{t}") for t in valid_types[12:]],
        ])
        await msg.delete()
        await update.message.reply_photo(
            photo=io.BytesIO(img_bytes),
            caption=caption,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    except Exception as e:
        await msg.edit_text(f"❌ Error: {e}")


async def weakness_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: `/weakness charizard`", parse_mode=ParseMode.MARKDOWN)
        return
    name = " ".join(context.args).lower()
    msg = await update.message.reply_text(f"🔍 Checking weaknesses for *{name.title()}*…", parse_mode=ParseMode.MARKDOWN)
    result = await get_pokemon(name)
    if not result:
        await msg.edit_text(f"❌ *{name.title()}* not found!", parse_mode=ParseMode.MARKDOWN)
        return
    poke = result["pokemon"]
    types = [t["type"]["name"] for t in poke.get("types", [])]
    w = get_weaknesses(types)
    type_str = " / ".join([f"{t.title()}{get_type_emoji(t)}" for t in types])
    lines = [f"⚠️ *{name.title()} — Weakness Chart*\n`Types: {type_str}`\n"]
    if w["double_weak"]:
        lines.append("🔴 *4× Weak:*\n" + "  ".join([f"`{get_type_emoji(t)} {t.title()}`" for t in w["double_weak"]]))
    if w["weak"]:
        lines.append("🟠 *2× Weak:*\n" + "  ".join([f"`{get_type_emoji(t)} {t.title()}`" for t in w["weak"]]))
    if w["immune"]:
        lines.append("🟢 *Immune:*\n" + "  ".join([f"`{get_type_emoji(t)} {t.title()}`" for t in w["immune"]]))
    if w["resist"]:
        lines.append("🔵 *Resistant:*\n" + "  ".join([f"`{get_type_emoji(t)} {t.title()}`" for t in w["resist"]]))
    await msg.edit_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def evsguid_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: `/evsguid charizard`", parse_mode=ParseMode.MARKDOWN)
        return
    name = " ".join(context.args).lower().strip()
    ev_builds = BEST_EVS.get(name)
    if not ev_builds:
        result = await get_pokemon(name)
        if not result:
            await update.message.reply_text(f"❌ *{name.title()}* not found!", parse_mode=ParseMode.MARKDOWN)
            return
        poke = result["pokemon"]
        stats = {s["stat"]["name"]: s["base_stat"] for s in poke.get("stats", [])}
        if stats.get("special-attack", 0) > stats.get("attack", 0):
            ev_builds = {"Special Sweeper": {"HP": 0, "Atk": 0, "Def": 4, "SpA": 252, "SpD": 0, "Spe": 252, "note": "Standard special attacker"}}
        else:
            ev_builds = {"Physical Sweeper": {"HP": 0, "Atk": 252, "Def": 4, "SpA": 0, "SpD": 0, "Spe": 252, "note": "Standard physical attacker"}}
    lines = [f"📈 *{name.title()} — EV Builds*\n"]
    for build_name, evs in ev_builds.items():
        evs_copy = dict(evs)
        note = evs_copy.pop("note", "")
        ev_str = " / ".join([f"{v} {k}" for k, v in evs_copy.items() if v > 0])
        lines.append(f"🏆 *{build_name}*\n`EVs: {ev_str}`")
        if note:
            lines.append(f"  _{note}_")
        lines.append("")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    if text.startswith("/"):
        return
    if text in NATURE_DATA:
        nat = NATURE_DATA[text]
        if nat["boost"]:
            reply = (
                f"🌿 *Nature: {text.title()}*\n\n"
                f"`Boosts  :` {nat['boost']} (+10%)\n"
                f"`Reduces :` {nat['reduce']} (−10%)\n\n"
                f"_{nat['desc']}_"
            )
        else:
            reply = f"🌿 *Nature: {text.title()}*\n\n_Neutral — no stat changes._"
        await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)
        return
    for query in [text, text.replace(" ", "-")]:
        move_data = await get_move(query)
        if move_data:
            move_type = move_data.get("type", {}).get("name", "?")
            dc = move_data.get("damage_class", {}).get("name", "?")
            power = move_data.get("power") or "—"
            accuracy = move_data.get("accuracy") or "—"
            pp = move_data.get("pp", "?")
            effect = ""
            for e in move_data.get("effect_entries", []):
                if e.get("language", {}).get("name") == "en":
                    effect = e.get("short_effect", "")
                    break
            emoji = get_type_emoji(move_type)
            reply = (
                f"🗡 *{text.replace('-',' ').title()}*\n\n"
                f"`Type     :` {move_type.title()} {emoji}\n"
                f"`Category :` {dc.title()}\n"
                f"`Power    :` {power}\n"
                f"`Accuracy :` {accuracy}%\n"
                f"`PP       :` {pp}\n"
            )
            if effect:
                reply += f"\n_{effect}_"
            await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)
            return


async def usertag_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context):
        await update.message.reply_text("❌ Admins only!")
        return
    if update.effective_chat.type == "private":
        await update.message.reply_text("❌ Groups only!")
        return
    msg_text = " ".join(context.args) if context.args else "Attention everyone! 📢"
    await update.message.reply_text(
        f"📢 *{msg_text}*\n\n_Tag sent to group members._",
        parse_mode=ParseMode.MARKDOWN
    )


async def pin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context):
        await update.message.reply_text("❌ Admins only!")
        return
    if update.message.reply_to_message:
        try:
            await context.bot.pin_chat_message(update.effective_chat.id, update.message.reply_to_message.message_id)
            await update.message.reply_text("📌 Message pinned!")
        except Exception as e:
            await update.message.reply_text(f"❌ Cannot pin: {e}")
    else:
        await update.message.reply_text("❌ Reply to a message to pin it!")


async def ban_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context):
        await update.message.reply_text("❌ Admins only!")
        return
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target:
        await update.message.reply_text("❌ Reply to the user you want to ban!")
        return
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await update.message.reply_text(f"🔨 *{target.first_name}* has been banned.", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"❌ Cannot ban: {e}")


async def unban_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context):
        await update.message.reply_text("❌ Admins only!")
        return
    if not context.args:
        await update.message.reply_text("Usage: `/unban @username`", parse_mode=ParseMode.MARKDOWN)
        return
    try:
        username = context.args[0].replace("@", "")
        member = await context.bot.get_chat_member(update.effective_chat.id, username)
        await context.bot.unban_chat_member(update.effective_chat.id, member.user.id)
        await update.message.reply_text(f"✅ *{member.user.first_name}* unbanned.", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"❌ Cannot unban: {e}")


async def mute_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context):
        await update.message.reply_text("❌ Admins only!")
        return
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target:
        await update.message.reply_text("❌ Reply to a user to mute them!")
        return
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, target.id, ChatPermissions(can_send_messages=False))
        await update.message.reply_text(f"🔇 *{target.first_name}* has been muted.", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"❌ Cannot mute: {e}")


async def setwelcome_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context):
        await update.message.reply_text("❌ Admins only!")
        return
    if not context.args:
        current = await get_welcome_message(update.effective_chat.id)
        await update.message.reply_text(
            f"Current welcome:\n`{current}`\n\nUsage: `/setwelcome Welcome {{name}}! 🎉`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    new_msg = " ".join(context.args)
    await set_welcome_message(update.effective_chat.id, new_msg)
    preview = new_msg.replace("{name}", update.effective_user.first_name)
    await update.message.reply_text(f"✅ Welcome message updated!\n\nPreview: {preview}")


async def like_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Give a like to another user by replying to their message."""
    msg = update.message
    if not msg or not msg.from_user:
        return

    if msg.chat.type not in ("group", "supergroup"):
        await msg.reply_text("❤️ The /like command only works in groups!")
        return

    if not msg.reply_to_message or not msg.reply_to_message.from_user:
        await msg.reply_text(
            "❤️ *How to use /like:*\nReply to someone's message and type `/like` to give them a like!",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    liker = msg.from_user
    liked = msg.reply_to_message.from_user

    if liked.is_bot:
        await msg.reply_text("🤖 You can't like a bot!")
        return

    if liker.id == liked.id:
        await msg.reply_text("😅 You can't like yourself!")
        return

    success = await give_like(liker.id, liked.id, msg.chat.id)
    total = await get_like_count(liked.id, msg.chat.id)
    liked_name = liked.first_name or liked.username or "that user"

    if success:
        await msg.reply_text(
            f"❤️ *{liker.first_name}* liked *{liked_name}*!\n"
            f"💖 *{liked_name}* now has `{total}` like(s) in this group.",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await msg.reply_text(
            f"⏳ You already liked *{liked_name}* today!\nCome back tomorrow to like again. 💫",
            parse_mode=ParseMode.MARKDOWN
        )


async def message_counter_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Count every non-command message in groups for the leaderboard."""
    msg = update.message
    if not msg or not msg.from_user:
        return
    if msg.chat.type not in ("group", "supergroup"):
        return

    user = msg.from_user
    if user.is_bot:
        return

    uid = user.id
    cid = msg.chat.id
    key = (uid, cid)
    now = time.time()
    text = (msg.text or "").strip()

    # Anti-flood check
    if muted_until.get(key, 0) > now:
        try:
            await msg.delete()
        except Exception:
            pass
        return

    timestamps = flood_log[key]
    timestamps.append(now)
    flood_log[key] = [t for t in timestamps if now - t <= FLOOD_WINDOW]

    if len(flood_log[key]) > FLOOD_LIMIT:
        until_ts = now + MUTE_DURATION
        muted_until[key] = until_ts
        flood_log[key] = []
        import datetime
        until_dt = datetime.datetime.fromtimestamp(until_ts, tz=datetime.timezone.utc)
        try:
            await context.bot.restrict_chat_member(
                cid, uid,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until_dt,
            )
            await msg.reply_text(
                f"⛔ *{user.first_name}* has been muted for 2 minutes due to flooding!",
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception:
            pass
        try:
            await msg.delete()
        except Exception:
            pass
        return

    # Skip duplicate consecutive messages (don't count spam)
    if text and last_text.get(key) == text.lower():
        return
    if text:
        last_text[key] = text.lower()

    # Count every group message (not just bot replies)
    try:
        await increment_message_count(
            uid, cid,
            username=user.username or "",
            first_name=user.first_name or "",
        )
    except Exception:
        pass


async def leaderboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return
    if msg.chat.type not in ("group", "supergroup"):
        await msg.reply_text("ℹ️ This command only works in groups.")
        return
    cid = msg.chat.id
    title = msg.chat.title or "Group"
    entries = await get_leaderboard(cid, limit=10)
    if not entries:
        await msg.reply_text("📊 No messages recorded yet. Start chatting!")
        return
    img_bytes = create_leaderboard_image(entries, chat_title=title)
    lines = [f"🏆 *POKE LEADERBOARD* — {title}\n"]
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    for i, e in enumerate(entries, 1):
        medal = medals.get(i, f"#{i} ")
        name = e.get("first_name") or e.get("username") or "Unknown"
        lines.append(f"{medal} *{name}* — `{e['count']:,}` msgs")
    caption = "\n".join(lines)
    await msg.reply_photo(
        photo=io.BytesIO(img_bytes),
        caption=caption,
        parse_mode=ParseMode.MARKDOWN,
    )


async def resetlb_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context):
        await update.message.reply_text("❌ Admins only!")
        return
    await reset_leaderboard(update.effective_chat.id)
    await update.message.reply_text("✅ Leaderboard reset for this group.")


async def broadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message to all users who have ever started the bot. Bot owner only."""
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("❌ Only the bot owner can use this command.")
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: `/broadcast Your message here`\n\n"
            "The message will be sent to every user who has started the bot.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    text = " ".join(context.args)
    broadcast_text = f"📣 *Broadcast Message*\n\n{text}"

    user_ids = await get_all_user_ids()
    if not user_ids:
        await update.message.reply_text("❌ No users found in the database.")
        return

    status_msg = await update.message.reply_text(
        f"📤 Sending broadcast to {len(user_ids)} users…"
    )

    sent = 0
    failed = 0
    for uid in user_ids:
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=broadcast_text,
                parse_mode=ParseMode.MARKDOWN,
            )
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)

    await status_msg.edit_text(
        f"✅ *Broadcast complete!*\n\n"
        f"📨 Sent: `{sent}`\n"
        f"❌ Failed: `{failed}` (blocked or never started bot)\n"
        f"👥 Total: `{len(user_ids)}`",
        parse_mode=ParseMode.MARKDOWN,
    )


async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        await add_user(member.id, member.username, member.first_name, member.last_name or "")
        welcome = await get_welcome_message(update.effective_chat.id)
        welcome_text = welcome.replace("{name}", f"*{member.first_name}*")
        await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return

    async def post_init(application):
        await init_db()
        logger.info("Database initialized.")
        # Register bot commands so they appear in the command list
        await application.bot.set_my_commands([
            BotCommand("start", "Start the bot"),
            BotCommand("help", "Show all commands"),
            BotCommand("data", "Pokémon info + stats (e.g. /data charizard)"),
            BotCommand("moveset", "Best competitive moveset"),
            BotCommand("bestnat", "Best natures for a Pokémon"),
            BotCommand("thype", "Type advantage chart"),
            BotCommand("weakness", "Weakness chart for a Pokémon"),
            BotCommand("evsguid", "EV build guide"),
            BotCommand("leaderboard", "Show group message leaderboard"),
            BotCommand("lb", "Show group message leaderboard (short)"),
            BotCommand("like", "Like a user — reply to their message"),
            BotCommand("resetlb", "Reset leaderboard (admin only)"),
            BotCommand("usertag", "Tag all users in group (admin)"),
            BotCommand("pin", "Pin a message (admin)"),
            BotCommand("ban", "Ban a user (admin)"),
            BotCommand("unban", "Unban a user (admin)"),
            BotCommand("mute", "Mute a user (admin)"),
            BotCommand("setwelcome", "Set welcome message (admin)"),
            BotCommand("broadcast", "Send message to all users (owner only)"),
        ])
        logger.info("Bot commands registered.")

    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("data", data_handler))
    app.add_handler(CommandHandler("moveset", moveset_handler))
    app.add_handler(CommandHandler("bestnat", bestnat_handler))
    app.add_handler(CommandHandler("thype", thype_handler))
    app.add_handler(CommandHandler("weakness", weakness_handler))
    app.add_handler(CommandHandler("weekness", weakness_handler))
    app.add_handler(CommandHandler("evsguid", evsguid_handler))
    app.add_handler(CommandHandler("usertag", usertag_handler))
    app.add_handler(CommandHandler("pin", pin_handler))
    app.add_handler(CommandHandler("ban", ban_handler))
    app.add_handler(CommandHandler("unban", unban_handler))
    app.add_handler(CommandHandler("mute", mute_handler))
    app.add_handler(CommandHandler("setwelcome", setwelcome_handler))
    app.add_handler(CommandHandler("leaderboard", leaderboard_handler))
    app.add_handler(CommandHandler("lb", leaderboard_handler))
    app.add_handler(CommandHandler("resetlb", resetlb_handler))
    app.add_handler(CommandHandler("like", like_handler))
    app.add_handler(CommandHandler("broadcast", broadcast_handler))

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    app.add_handler(CallbackQueryHandler(callback_handler))

    # Group 0: message counter + anti-flood (runs on ALL non-command text in groups)
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS, message_counter_handler),
        group=0,
    )
    # Group 1: inline Pokémon search (move/nature lookup)
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, search_handler),
        group=1,
    )

    logger.info("Bot is running...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
