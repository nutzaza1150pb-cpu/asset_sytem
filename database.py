"""
database.py
------------
รวมฟังก์ชันทั้งหมดที่เกี่ยวกับฐานข้อมูล SQLite (assets.db)
- ผู้ใช้งาน (users) : login, สิทธิ์ admin / user
- ครุภัณฑ์ (assets) : เพิ่ม / แก้ไข / ลบ / ค้นหา พร้อมรูปภาพ

ใช้ SQLite เพราะเป็นไฟล์เดียว ไม่ต้องติดตั้งเซิร์ฟเวอร์ฐานข้อมูลเพิ่ม
ย้ายเครื่อง/สำรองข้อมูล แค่ก็อปไฟล์ assets.db (และโฟลเดอร์ asset_images) ไปก็พอ
"""

import hashlib
import os
import sqlite3
from datetime import datetime

DB_PATH = "assets.db"
IMAGE_DIR = "asset_images"

# คอลัมน์ข้อมูลครุภัณฑ์ (ใช้ชื่อภาษาไทยเดิมให้ตรงกับระบบเก่า)
ASSET_FIELDS = [
    "asset_no",        # หมายเลขครุภัณฑ์
    "item_name",        # รายการ
    "item_date",        # วันเดือนปี
    "acquire_method",   # วิธีได้มา
    "receive_qty",      # รับระหว่างปี - จำนวน
    "receive_amount",   # รับระหว่างปี - จำนวนเงิน
    "lost_qty",         # จำนวนสูญหาย
    "remain_qty",       # คงเหลือ - จำนวน
    "remain_amount",    # คงเหลือ - จำนวนเงิน
    "location",         # สถานที่ใช้ครุภัณฑ์
    "condition",        # สภาพการใช้งาน
    "remark",           # หมายเหตุ
    "image_path",       # พาธไฟล์รูปภาพ
]

STATUS_OPTIONS = ["ใช้งานได้ปกติ", "ชำรุด", "รอซ่อม", "จำหน่ายแล้ว"]
STATUS_UNSET = "ยังไม่ระบุ"
ALL_STATUSES = STATUS_OPTIONS + [STATUS_UNSET]
STATUS_ICON = {
    "ใช้งานได้ปกติ": "🟢",
    "ชำรุด": "🔴",
    "รอซ่อม": "🟡",
    "จำหน่ายแล้ว": "⚪",
    STATUS_UNSET: "❓",
}


# ---------------------------------------------------------------------------
# การเชื่อมต่อฐานข้อมูล
# ---------------------------------------------------------------------------
def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """สร้างตารางและผู้ใช้ admin เริ่มต้น (รันทุกครั้งตอนเปิดแอป ปลอดภัย ไม่ทับข้อมูลเดิม)"""
    os.makedirs(IMAGE_DIR, exist_ok=True)
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            full_name TEXT,
            role TEXT NOT NULL CHECK(role IN ('admin', 'user')),
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_no TEXT UNIQUE NOT NULL,
            item_name TEXT,
            item_date TEXT,
            acquire_method TEXT,
            receive_qty REAL DEFAULT 0,
            receive_amount REAL DEFAULT 0,
            lost_qty REAL DEFAULT 0,
            remain_qty REAL DEFAULT 0,
            remain_amount REAL DEFAULT 0,
            location TEXT,
            condition TEXT,
            remark TEXT,
            image_path TEXT,
            created_by TEXT,
            updated_at TEXT
        )
    """)
    conn.commit()

    # สร้างผู้ใช้ admin เริ่มต้น ถ้ายังไม่มีผู้ใช้เลยในระบบ
    cur.execute("SELECT COUNT(*) AS c FROM users")
    if cur.fetchone()["c"] == 0:
        create_user("admin", "admin1234", "ผู้ดูแลระบบ", "admin")

    conn.close()


# ---------------------------------------------------------------------------
# ผู้ใช้งาน / การล็อคอิน
# ---------------------------------------------------------------------------
def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000
    ).hex()


def create_user(username: str, password: str, full_name: str, role: str) -> tuple[bool, str]:
    """สร้างผู้ใช้ใหม่ คืนค่า (สำเร็จหรือไม่, ข้อความ)"""
    username = username.strip()
    if not username or not password:
        return False, "กรุณากรอกชื่อผู้ใช้และรหัสผ่านให้ครบ"
    if len(password) < 4:
        return False, "รหัสผ่านควรมีอย่างน้อย 4 ตัวอักษร"

    salt = os.urandom(16).hex()
    pwd_hash = _hash_password(password, salt)

    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, full_name, role, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (username, pwd_hash, salt, full_name, role, datetime.now().isoformat()),
        )
        conn.commit()
        return True, "สร้างผู้ใช้เรียบร้อยแล้ว"
    except sqlite3.IntegrityError:
        return False, f"มีชื่อผู้ใช้ '{username}' อยู่ในระบบแล้ว"
    finally:
        conn.close()


def verify_login(username: str, password: str):
    """ตรวจสอบ username/password คืนค่า dict ผู้ใช้ถ้าถูกต้อง หรือ None ถ้าไม่ถูกต้อง"""
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if row is None:
        return None
    if _hash_password(password, row["salt"]) == row["password_hash"]:
        return dict(row)
    return None


def change_password(username: str, new_password: str) -> tuple[bool, str]:
    if len(new_password) < 4:
        return False, "รหัสผ่านควรมีอย่างน้อย 4 ตัวอักษร"
    salt = os.urandom(16).hex()
    pwd_hash = _hash_password(new_password, salt)
    conn = get_connection()
    conn.execute(
        "UPDATE users SET password_hash = ?, salt = ? WHERE username = ?",
        (pwd_hash, salt, username),
    )
    conn.commit()
    conn.close()
    return True, "เปลี่ยนรหัสผ่านเรียบร้อยแล้ว"


def list_users():
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, username, full_name, role, created_at FROM users ORDER BY id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_user(username: str) -> tuple[bool, str]:
    if username == "admin":
        return False, "ไม่สามารถลบผู้ใช้ admin หลักได้"
    conn = get_connection()
    conn.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    return True, "ลบผู้ใช้เรียบร้อยแล้ว"


# ---------------------------------------------------------------------------
# ครุภัณฑ์ (assets)
# ---------------------------------------------------------------------------
def add_asset(data: dict, created_by: str) -> tuple[bool, str]:
    conn = get_connection()
    try:
        cols = ASSET_FIELDS
        placeholders = ", ".join(["?"] * len(cols))
        values = [data.get(c) for c in cols]
        conn.execute(
            f"INSERT INTO assets ({', '.join(cols)}, created_by, updated_at) "
            f"VALUES ({placeholders}, ?, ?)",
            values + [created_by, datetime.now().isoformat()],
        )
        conn.commit()
        return True, "บันทึกข้อมูลเรียบร้อยแล้ว ✅"
    except sqlite3.IntegrityError:
        return False, f"หมายเลขครุภัณฑ์ '{data.get('asset_no')}' มีอยู่ในระบบแล้ว"
    finally:
        conn.close()


def update_asset(asset_id: int, data: dict) -> tuple[bool, str]:
    conn = get_connection()
    try:
        cols = ASSET_FIELDS
        set_clause = ", ".join([f"{c} = ?" for c in cols])
        values = [data.get(c) for c in cols]
        conn.execute(
            f"UPDATE assets SET {set_clause}, updated_at = ? WHERE id = ?",
            values + [datetime.now().isoformat(), asset_id],
        )
        conn.commit()
        return True, "แก้ไขข้อมูลเรียบร้อยแล้ว ✅"
    except sqlite3.IntegrityError:
        return False, f"หมายเลขครุภัณฑ์ '{data.get('asset_no')}' ซ้ำกับรายการอื่น"
    finally:
        conn.close()


def delete_asset(asset_id: int) -> None:
    conn = get_connection()
    row = conn.execute("SELECT image_path FROM assets WHERE id = ?", (asset_id,)).fetchone()
    if row and row["image_path"] and os.path.exists(row["image_path"]):
        try:
            os.remove(row["image_path"])
        except OSError:
            pass
    conn.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
    conn.commit()
    conn.close()


def get_all_assets():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM assets ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_asset_by_id(asset_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM assets WHERE id = ?", (asset_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def asset_no_exists(asset_no: str, exclude_id: int = None) -> bool:
    conn = get_connection()
    if exclude_id is None:
        row = conn.execute(
            "SELECT 1 FROM assets WHERE asset_no = ?", (asset_no,)
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT 1 FROM assets WHERE asset_no = ? AND id != ?", (asset_no, exclude_id)
        ).fetchone()
    conn.close()
    return row is not None


def save_uploaded_image(uploaded_file, asset_no: str) -> str:
    """บันทึกไฟล์รูปที่อัปโหลดลงโฟลเดอร์ asset_images คืนค่าพาธไฟล์"""
    os.makedirs(IMAGE_DIR, exist_ok=True)
    ext = os.path.splitext(uploaded_file.name)[1].lower() or ".jpg"
    safe_no = "".join(c for c in asset_no if c.isalnum() or c in ("-", "_")) or "asset"
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{safe_no}_{timestamp}{ext}"
    path = os.path.join(IMAGE_DIR, filename)
    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return path
