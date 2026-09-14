"""
app.py — ระบบจัดการครุภัณฑ์ (มีระบบล็อคอิน + ฐานข้อมูล + รูปภาพ)
รันด้วยคำสั่ง:  streamlit run app.py
"""

import os
from datetime import date, datetime

import pandas as pd
import streamlit as st

import database as db

st.set_page_config(page_title="ระบบจัดการครุภัณฑ์", page_icon="🗂️", layout="wide")

# ---------------------------------------------------------------------------
# CSS ปรับให้ตัวอักษร/ปุ่มใหญ่ขึ้น เหมาะกับผู้สูงอายุ / ใช้งานง่าย
# ---------------------------------------------------------------------------
st.markdown("""
<style>
html, body, [class*="css"]  { font-size: 18px; }
h1 { font-size: 2.1rem !important; }
h2 { font-size: 1.6rem !important; }
h3 { font-size: 1.35rem !important; }
.stButton > button {
    font-size: 18px !important;
    padding: 0.6rem 1.2rem !important;
    border-radius: 10px !important;
    font-weight: 600;
}
.stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"], .stDateInput input {
    font-size: 18px !important;
}
div[data-testid="stMetricValue"] { font-size: 1.5rem !important; }
.login-box {
    max-width: 420px;
    margin: 40px auto;
    padding: 30px;
    border-radius: 16px;
    border: 1px solid #e0e0e0;
    box-shadow: 0 4px 14px rgba(0,0,0,0.06);
}
</style>
""", unsafe_allow_html=True)

db.init_db()

# ---------------------------------------------------------------------------
# ส่วนล็อคอิน
# ---------------------------------------------------------------------------
def login_page():
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.image("photos/1-removebg-preview.png",width=150)
        st.markdown("## 🗂️ ระบบจัดการครุภัณฑ์")
        st.markdown("#### เข้าสู่ระบบ")
        username = st.text_input("👤 ชื่อผู้ใช้")
        password = st.text_input("🔒 รหัสผ่าน", type="password")
        st.write("")
        if st.button("➡️ เข้าสู่ระบบ", type="primary", use_container_width=True):
            user = db.verify_login(username.strip(), password)
            if user:
                st.session_state["user"] = user
                st.rerun()
            else:
                st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง")



def logout_button():
    with st.sidebar:
        st.markdown(f"### 👋 สวัสดีคุณ {st.session_state['user']['full_name'] or st.session_state['user']['username']}")
        role_label = "ผู้ดูแลระบบ (Admin)" if st.session_state["user"]["role"] == "admin" else "ผู้ใช้งานทั่วไป (User)"
        st.caption(f"สิทธิ์การใช้งาน: {role_label}")
        if st.button("🚪 ออกจากระบบ", use_container_width=True):
            del st.session_state["user"]
            st.rerun()
        st.divider()
        with st.expander("🔑 เปลี่ยนรหัสผ่าน"):
            new_pw = st.text_input("รหัสผ่านใหม่", type="password", key="chg_pw")
            new_pw2 = st.text_input("ยืนยันรหัสผ่านใหม่", type="password", key="chg_pw2")
            if st.button("บันทึกรหัสผ่านใหม่", key="chg_pw_btn"):
                if new_pw != new_pw2:
                    st.error("รหัสผ่านทั้งสองช่องไม่ตรงกัน")
                else:
                    ok, msg = db.change_password(st.session_state["user"]["username"], new_pw)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)


# ---------------------------------------------------------------------------
# ฟอร์มกรอกข้อมูลครุภัณฑ์ (ใช้ทั้งตอนเพิ่มและตอนแก้ไข)
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# ฟอร์มกรอกข้อมูลครุภัณฑ์ (ย้ายช่องวันเดือนปีไปไว้ล่างสุด)
# ---------------------------------------------------------------------------
def asset_form(existing: dict = None, form_key: str = "add_form"):
    """แสดงฟอร์มกรอกข้อมูล คืนค่า dict ข้อมูล + ไฟล์รูปที่อัปโหลด (ถ้ามี) เมื่อกดบันทึก"""
    e = existing or {}

    def parse_date(val):
        try:
            return datetime.strptime(str(val)[:10], "%Y-%m-%d").date()
        except Exception:
            return date.today()

    st.markdown("##### ข้อมูลพื้นฐาน")
    col1, col2 = st.columns(2)
    with col1:
        asset_no = st.text_input("หมายเลขครุภัณฑ์ *", value=e.get("asset_no", ""), key=f"{form_key}_no")
        item_name = st.text_input("รายการ", value=e.get("item_name", ""), key=f"{form_key}_name")
        # ❌ ตัด st.date_input จากจุดนี้ออก
    with col2:
        acquire_options = ["ซื้อ", "จ้าง", "ตกลงราคา", "อื่นๆ"]
        default_acquire = e.get("acquire_method") if e.get("acquire_method") in acquire_options else acquire_options[0]
        acquire_method = st.selectbox(
            "วิธีได้มา (ซื้อ/จ้าง)", acquire_options,
            index=acquire_options.index(default_acquire), key=f"{form_key}_acquire",
        )
        location = st.text_input("สถานที่ใช้ครุภัณฑ์ / งาน/โครงการ", value=e.get("location", ""), key=f"{form_key}_loc")

    default_cond = e.get("condition") if e.get("condition") in db.STATUS_OPTIONS else db.STATUS_OPTIONS[0]
    condition = st.selectbox(
        "สภาพการใช้งาน", db.STATUS_OPTIONS,
        index=db.STATUS_OPTIONS.index(default_cond), key=f"{form_key}_cond",
    )

    st.markdown("##### รับระหว่างปี")
    col3, col4 = st.columns(2)
    with col3:
        receive_qty = st.number_input("จำนวน (หน่วย)", min_value=0.0, step=1.0,
                                       value=float(e.get("receive_qty") or 0), key=f"{form_key}_rq")
    with col4:
        receive_amount = st.number_input("จำนวนเงิน (บาท)", min_value=0.0, step=0.01,
                                          value=float(e.get("receive_amount") or 0), key=f"{form_key}_ra")

    lost_qty = st.number_input("จำนวนสูญหาย (หน่วย)", min_value=0.0, step=1.0,
                                value=float(e.get("lost_qty") or 0), key=f"{form_key}_lq")

    st.markdown("##### คงเหลือ")
    col5, col6 = st.columns(2)
    with col5:
        remain_qty = st.number_input("จำนวน (หน่วย)", min_value=0.0, step=1.0,
                                      value=float(e.get("remain_qty") or 0), key=f"{form_key}_mq")
    with col6:
        remain_amount = st.number_input("จำนวนเงิน (บาท)", min_value=0.0, step=0.01,
                                         value=float(e.get("remain_amount") or 0), key=f"{form_key}_ma")

    remark = st.text_input("หมายเหตุ", value=e.get("remark", ""), key=f"{form_key}_remark")

    st.markdown("##### 📷 รูปภาพครุภัณฑ์")
    if e.get("image_path") and os.path.exists(e["image_path"]):
        st.image(e["image_path"], width=220, caption="รูปปัจจุบัน")
    uploaded_image = st.file_uploader(
        "อัปโหลดรูปภาพ (jpg / png) — ถ้าไม่เลือกไฟล์ใหม่ จะใช้รูปเดิม",
        type=["jpg", "jpeg", "png"], key=f"{form_key}_img",
    )

    # 🟢 ✅ [เพิ่มจุดนี้] ย้ายช่องวันเดือนปีมาไว้ส่วนล่างสุด
    st.markdown("##### 📅 วันที่รับ/วันเดือนปี")
    item_date = st.date_input(
        "วันเดือนปีที่รับครุภัณฑ์",
        value=parse_date(e["item_date"]) if e.get("item_date") else date.today(),
        key=f"{form_key}_date",
    )

    data = {
        "asset_no": asset_no.strip(),
        "item_name": item_name.strip(),
        "item_date": item_date.strftime("%Y-%m-%d"),
        "acquire_method": acquire_method,
        "receive_qty": receive_qty,
        "receive_amount": receive_amount,
        "lost_qty": lost_qty,
        "remain_qty": remain_qty,
        "remain_amount": remain_amount,
        "location": location.strip(),
        "condition": condition,
        "remark": remark.strip(),
        "image_path": e.get("image_path"),
    }
    return data, uploaded_image


# ---------------------------------------------------------------------------
# แท็บ: เพิ่มข้อมูล (admin เท่านั้น)
# ---------------------------------------------------------------------------
def tab_add():
    st.subheader("➕ เพิ่มครุภัณฑ์ใหม่")
    data, uploaded_image = asset_form(form_key="add")
    if st.button("💾 บันทึกข้อมูล", type="primary"):
        if not data["asset_no"]:
            st.error("กรุณากรอก 'หมายเลขครุภัณฑ์' ก่อนบันทึก")
        elif db.asset_no_exists(data["asset_no"]):
            st.error(f"หมายเลขครุภัณฑ์ '{data['asset_no']}' มีอยู่ในระบบแล้ว กรุณาใช้เลขอื่น")
        else:
            if uploaded_image is not None:
                data["image_path"] = db.save_uploaded_image(uploaded_image, data["asset_no"])
            ok, msg = db.add_asset(data, st.session_state["user"]["username"])
            if ok:
                st.success(msg)
                st.balloons()
            else:
                st.error(msg)


# ---------------------------------------------------------------------------
# แท็บ: ดูข้อมูล / แก้ไข / ลบ
# ---------------------------------------------------------------------------
def dashboard(df: pd.DataFrame):
    if len(df) == 0:
        return
    status_series = df["condition"].astype(str).replace({"": db.STATUS_UNSET, "None": db.STATUS_UNSET, "nan": db.STATUS_UNSET})
    counts = status_series.value_counts()
    cols = st.columns(len(db.ALL_STATUSES))
    for col, status in zip(cols, db.ALL_STATUSES):
        col.metric(f"{db.STATUS_ICON[status]} {status}", f"{int(counts.get(status, 0))} รายการ")
    st.divider()


SORT_OPTIONS = {
    "ลำดับที่เพิ่มล่าสุด": None,  # ใช้ค่าเรียงตาม id ตามปกติ
    "วันเดือนปี (เก่าสุด → ใหม่สุด)": ("item_date", True),
    "วันเดือนปี (ใหม่สุด → เก่าสุด)": ("item_date", False),
    "หมายเลขครุภัณฑ์ (ก-ฮ / A-Z)": ("asset_no", True),
    "ชื่อรายการ (ก-ฮ / A-Z)": ("item_name", True),
}


def filter_ui(df: pd.DataFrame):
    col_search, col_filter = st.columns([3, 1])
    with col_search:
        search_term = st.text_input("🔍 ค้นหา (หมายเลขครุภัณฑ์ / รายการ / สถานที่ ฯลฯ)")
    with col_filter:
        status_filter = st.selectbox("กรองตามสถานะ", ["ทั้งหมด"] + db.ALL_STATUSES)
 
    sort_choice = st.selectbox("↕️ เรียงลำดับ", list(SORT_OPTIONS.keys()))
 
    result = df.copy()
    if search_term:
        mask = result.astype(str).apply(lambda c: c.str.contains(search_term, case=False, na=False)).any(axis=1)
        result = result[mask]
    if status_filter != "ทั้งหมด":
        status_series = result["condition"].astype(str).replace({"": db.STATUS_UNSET, "None": db.STATUS_UNSET})
        result = result[status_series == status_filter]
 
    sort_spec = SORT_OPTIONS[sort_choice]
    if sort_spec is not None:
        sort_col, ascending = sort_spec
        result = result.sort_values(by=sort_col, ascending=ascending, na_position="last", kind="stable")
 
    return result


COLUMN_LABELS = {
    "id": "รหัส",
    "asset_no": "หมายเลขครุภัณฑ์",
    "item_name": "รายการ",
    "item_date": "วันเดือนปี",
    "acquire_method": "วิธีได้มา",
    "receive_qty": "รับ-จำนวน",
    "receive_amount": "รับ-เงิน",
    "lost_qty": "สูญหาย",
    "remain_qty": "คงเหลือ-จำนวน",
    "remain_amount": "คงเหลือ-เงิน",
    "location": "สถานที่",
    "condition": "สภาพ",
    "remark": "หมายเหตุ",
}


def tab_view(is_admin: bool):
    st.subheader("🔍 ค้นหา / ดูข้อมูลครุภัณฑ์")
    assets = db.get_all_assets()
    df = pd.DataFrame(assets) if assets else pd.DataFrame(columns=["id"] + db.ASSET_FIELDS)

    st.caption(f"ทั้งหมด {len(df)} รายการ")
    dashboard(df)
    result = filter_ui(df)
    st.caption(f"พบ {len(result)} รายการ")

    if len(result) == 0:
        st.info("ไม่พบข้อมูล")
        return

    view_mode = st.radio("รูปแบบการแสดงผล", ["🖼️ แบบการ์ด (เห็นรูป)", "📋 แบบตาราง"], horizontal=True)

    if view_mode.startswith("🖼️"):
        for _, row in result.iterrows():
            asset_id = int(row["id"])
            edit_key = f"inline_edit_{asset_id}"
            confirm_key = f"inline_confirm_del_{asset_id}"

            with st.container(border=True):
                c1, c2 = st.columns([1, 3])
                with c1:
                    if row.get("image_path") and os.path.exists(str(row["image_path"])):
                        st.image(row["image_path"], width=150)
                    else:
                        st.markdown("📦 *ไม่มีรูปภาพ*")
                with c2:
                    st.markdown(f"**{row['item_name'] or '(ไม่ระบุชื่อรายการ)'}**")
                    st.write(f"หมายเลขครุภัณฑ์: `{row['asset_no']}`")
                    status = row["condition"] or db.STATUS_UNSET
                    st.write(f"สถานะ: {db.STATUS_ICON.get(status,'❓')} {status}")
                    st.write(f"สถานที่: {row['location'] or '-'}  |  วันที่: {row['item_date'] or '-'}")
                    if row.get("remark"):
                        st.caption(f"หมายเหตุ: {row['remark']}")

                    if is_admin:
                        bcol1, bcol2 = st.columns(2)
                        with bcol1:
                            btn_label = "🔒 ปิดแก้ไข" if st.session_state.get(edit_key) else "✏️ แก้ไข"
                            if st.button(btn_label, key=f"edit_btn_{asset_id}"):
                                if st.session_state.get(edit_key):
                                    del st.session_state[edit_key]
                                else:
                                    st.session_state[edit_key] = True
                                st.rerun()
                        with bcol2:
                            if st.button("🗑️ ลบ", key=f"del_{asset_id}"):
                                st.session_state[confirm_key] = True
                                st.rerun()

                # ยืนยันลบ inline
                if is_admin and st.session_state.get(confirm_key):
                    st.warning(f"⚠️ ยืนยันลบ '{row['asset_no']}' — {row['item_name']} ใช่หรือไม่?")
                    dc1, dc2 = st.columns(2)
                    with dc1:
                        if st.button("✅ ยืนยันลบ", key=f"confirm_yes_{asset_id}", type="primary"):
                            db.delete_asset(asset_id)
                            del st.session_state[confirm_key]
                            st.success("ลบข้อมูลเรียบร้อยแล้ว")
                            st.rerun()
                    with dc2:
                        if st.button("❌ ยกเลิก", key=f"confirm_no_{asset_id}"):
                            del st.session_state[confirm_key]
                            st.rerun()

                # ฟอร์มแก้ไข inline
                if is_admin and st.session_state.get(edit_key):
                    st.divider()
                    st.markdown("##### ✏️ แก้ไขข้อมูล")
                    asset = db.get_asset_by_id(asset_id)
                    if asset:
                        data, uploaded_image = asset_form(existing=asset, form_key=f"ie_{asset_id}")
                        ec1, ec2 = st.columns(2)
                        with ec1:
                            if st.button("💾 บันทึก", key=f"save_{asset_id}", type="primary"):
                                if not data["asset_no"]:
                                    st.error("กรุณากรอกหมายเลขครุภัณฑ์")
                                elif db.asset_no_exists(data["asset_no"], exclude_id=asset_id):
                                    st.error(f"หมายเลขครุภัณฑ์ '{data['asset_no']}' ซ้ำกับรายการอื่น")
                                else:
                                    if uploaded_image is not None:
                                        data["image_path"] = db.save_uploaded_image(uploaded_image, data["asset_no"])
                                    ok, msg = db.update_asset(asset_id, data)
                                    if ok:
                                        del st.session_state[edit_key]
                                        st.success(msg)
                                        st.rerun()
                                    else:
                                        st.error(msg)
                        with ec2:
                            if st.button("❌ ยกเลิก", key=f"cancel_{asset_id}"):
                                del st.session_state[edit_key]
                                st.rerun()
    else:
        # ตัดคอลัมน์ id (รหัส), created_by และ updated_at ออก เพื่อความสะอาดเรียบร้อย
        display_df = result.drop(columns=["id", "image_path", "created_by", "updated_at"], errors="ignore").rename(columns=COLUMN_LABELS)
        
        # จัดลำดับคอลัมน์ใหม่ ดึง 'วันเดือนปี' ออกมาไว้ท้ายสุด
        if "วันเดือนปี" in display_df.columns:
            cols = [c for c in display_df.columns if c != "วันเดือนปี"] + ["วันเดือนปี"]
            display_df = display_df[cols]
            
        st.dataframe(display_df, use_container_width=True, height=420)

    # ดาวน์โหลด
    st.divider()
    csv = result.drop(columns=["image_path"], errors="ignore").rename(columns=COLUMN_LABELS).to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ ดาวน์โหลดผลลัพธ์เป็น CSV", data=csv, file_name="assets_filtered.csv", mime="text/csv")


# ---------------------------------------------------------------------------
# แท็บ: นำเข้าจาก Excel (admin เท่านั้น)
# ---------------------------------------------------------------------------

# ชีตที่ไม่ใช่ข้อมูลครุภัณฑ์ให้ข้ามไป
_SKIP_SHEETS = {"สรุปรวม", "Sheet2", "Sheet3", "MIS", "ปรับ(1)", "ปรับปรุง"}

# คำหลักที่บ่งบอกว่าแถวนั้นคือ header ของตารางครุภัณฑ์
_HEADER_KEYWORDS = ("หมายเลขครุภัณฑ์", "หมายเลข", "รหัสครุภัณฑ์", "รหัสพัสดุ")

# ชื่อคอลัมน์ที่เป็นไปได้ → field ใน DB (จับคู่แบบ substring, strip ช่องว่างก่อนจับ)
_COL_ALIASES: list[tuple[str, str]] = [
    # asset_no — ลำดับสำคัญ: จับเฉพาะ→ทั่วไป
    ("หมายเลขครุภัณฑ์", "asset_no"),
    ("รหัสครุภัณฑ์", "asset_no"),
    ("หมายเลข", "asset_no"),      # จับ "หมายเลข              ครุภัณฑ์" หลัง re.sub ช่องว่าง
    # item_name
    ("รายการ", "item_name"),
    ("ชื่อครุภัณฑ์", "item_name"),
    # item_date
    ("วัน เดือน ปี", "item_date"),
    ("วันเดือนปี", "item_date"),
    ("วันที่รับ", "item_date"),
    # acquire_method
    ("วิธีได้มา", "acquire_method"),
    ("วิธีการได้มา", "acquire_method"),
    # receive_qty  (ต้องมาก่อน remain_qty เพราะ substring ซ้ำกัน)
    ("จ.น. รับ", "receive_qty"),
    # receive_amount
    ("มูลค่าเริ่มต้น", "receive_amount"),
    # remain_qty
    ("คงเหลือ", "remain_qty"),       # จับแบบ fallback ถ้าไม่มีชื่อชัด
    # remain_amount
    ("มูลค่าคงเหลือ", "remain_amount"),
    # location
    ("สถานที่ใช้ครุภัณฑ์", "location"),
    ("สถานที่", "location"),
    ("งาน/โครงการ", "location"),
    # condition
    ("สภาพการใช้งาน", "condition"),
    ("สภาพ", "condition"),
    ("สถานะ", "condition"),
    # remark
    ("หมายเหตุ", "remark"),
    ("คุณสมบัติเฉพาะ", "remark"),
    ("แหล่งเงิน", "remark"),
]

# ชีตแบบ flat (ไม่มี header row พิเศษ) — คอลัมน์แรกเป็น header ปกติ
_FLAT_SHEET_NAMES = {"Sheet1", "ปรับปรุง"}

# สัญลักษณ์ที่ถือว่า "ว่าง"
_NULL_STRINGS = {"nan", "none", "null", "", "nat", "-", "–", "—", "n/a"}


def clean_number_val(val, default_val=0.0):
    """แปลงค่าเป็นตัวเลข รองรับ comma, แดช, ค่าว่าง, datetime"""
    if val is None:
        return default_val
    # datetime object จาก openpyxl → ดึงแค่ timestamp
    if hasattr(val, "timestamp"):
        return default_val
    try:
        if pd.isna(val):
            return default_val
    except (TypeError, ValueError):
        pass
    s = str(val).strip().replace(",", "")
    if s.lower() in _NULL_STRINGS:
        return default_val
    try:
        num = float(s)
        return int(num) if num == int(num) else num
    except (ValueError, OverflowError):
        return default_val


def _parse_thai_date(val) -> str:
    """แปลงวันที่หลายรูปแบบ → YYYY-MM-DD (คร่าวๆ, ไม่ crash ถ้าอ่านไม่ได้)"""
    if val is None:
        return ""
    # datetime/Timestamp จาก openpyxl/pandas
    if hasattr(val, "strftime"):
        try:
            return val.strftime("%Y-%m-%d")
        except Exception:
            return ""
    s = str(val).strip()
    if not s or s.lower() in _NULL_STRINGS:
        return ""
    # ISO format ที่ขึ้นต้นด้วย YYYY-MM-DD
    if len(s) >= 10 and s[4] == "-":
        return s[:10]
    # ลองใช้ pandas parse (รองรับหลาย format)
    try:
        dt = pd.to_datetime(s, dayfirst=True, errors="coerce")
        if pd.notna(dt):
            # ปรับปี พ.ศ. → ค.ศ. ถ้าปีใหญ่กว่า 2100
            if dt.year > 2100:
                dt = dt.replace(year=dt.year - 543)
            return dt.strftime("%Y-%m-%d")
    except Exception:
        pass
    return ""


def _col_map(columns: list[str]) -> dict[str, str]:
    """จับคู่ชื่อคอลัมน์จริงกับ field ใน DB (คืน dict col_name→field)
    - normalize ช่องว่างหลายตัวเป็นตัวเดียวก่อนจับคู่
    - คืน key เป็นชื่อคอลัมน์จริง (ยังไม่ normalize) เพื่อใช้อ้างอิง df
    """
    import re
    mapping: dict[str, str] = {}
    assigned: set[str] = set()
    for col in columns:
        col_raw = str(col).strip()
        col_norm = re.sub(r"\s+", " ", col_raw)  # ยุบช่องว่างซ้ำ
        for alias, field in _COL_ALIASES:
            if field not in assigned and alias in col_norm:
                mapping[col_raw] = field
                assigned.add(field)
                break
    return mapping


def _detect_format(df_raw: pd.DataFrame) -> tuple[int | None, bool]:
    """
    หาแถว header และตัดสินว่าเป็น flat format หรือเปล่า
    คืน (header_row_idx, is_flat)
    """
    for idx in range(min(10, len(df_raw))):
        row_vals = [str(v).strip() for v in df_raw.iloc[idx].values if pd.notna(v) and str(v).strip()]
        row_str = " ".join(row_vals)
        # ตรวจว่าแถวนี้มี keyword ของ header
        if any(kw in row_str for kw in _HEADER_KEYWORDS):
            # ถ้าแถวแรก (idx==0) มี keyword → flat table
            return idx, (idx == 0)
    return None, False


def _read_sheet(xls: pd.ExcelFile, sheet_name: str, engine: str) -> pd.DataFrame | None:
    """อ่าน 1 ชีต → DataFrame ที่มี column ชัดเจน หรือ None ถ้าไม่มีข้อมูล"""
    df_raw = pd.read_excel(xls, sheet_name=sheet_name, engine=engine, header=None)
    header_idx, is_flat = _detect_format(df_raw)

    if header_idx is None:
        return None  # ไม่เจอ header → ข้ามชีตนี้

    if is_flat:
        # flat: แถว header_idx คือ column names, ข้อมูลเริ่ม header_idx+1
        df_raw.columns = [str(c).strip() for c in df_raw.iloc[header_idx]]
        df = df_raw.iloc[header_idx + 1:].reset_index(drop=True)
    else:
        # รายงาน: header อาจซ้อน 2 แถว (header_idx และ header_idx+1)
        # ใช้แถวบนเป็นหลัก ถ้าเซลล์ว่างให้ใช้แถวล่าง
        top = [str(v).strip() if pd.notna(v) else "" for v in df_raw.iloc[header_idx]]
        if header_idx + 1 < len(df_raw):
            bot = [str(v).strip() if pd.notna(v) else "" for v in df_raw.iloc[header_idx + 1]]
        else:
            bot = [""] * len(top)
        merged = [t if t else b for t, b in zip(top, bot)]
        df_raw.columns = merged
        df = df_raw.iloc[header_idx + 2:].reset_index(drop=True)

    df = df.dropna(how="all")
    if df.empty:
        return None
    return df


def _df_to_assets(df: pd.DataFrame) -> list[dict]:
    """แปลง DataFrame (ชีตเดียว) → list of asset dict พร้อมใส่ใน DB"""
    mapping = _col_map(list(df.columns))
    if "asset_no" not in mapping.values():
        return []  # ไม่มีคอลัมน์หมายเลขครุภัณฑ์ → ข้าม

    # reverse mapping: field → col_name
    rev = {v: k for k, v in mapping.items()}

    def gv(field: str, default="") -> str:
        col = rev.get(field)
        if col is None or col not in df.columns:
            return default
        val = df[col]
        return val

    results = []
    for _, row in df.iterrows():
        def get(field, default=""):
            col = rev.get(field)
            if col is None:
                return default
            v = row.get(col, default)
            if v is None:
                return default
            try:
                if pd.isna(v):
                    return default
            except (TypeError, ValueError):
                pass
            s = str(v).strip()
            return default if s.lower() in _NULL_STRINGS else s

        asset_no = get("asset_no")
        if not asset_no:
            continue
        # กรองแถวที่เป็น header หลุดมา
        if any(kw in asset_no for kw in _HEADER_KEYWORDS):
            continue
        # กรองแถวที่ asset_no ดูเหมือน label ไม่ใช่เลขครุภัณฑ์
        if len(asset_no) < 3 or asset_no.isdigit():
            continue

        receive_qty = clean_number_val(get("receive_qty", "1"), 1)
        receive_amount = clean_number_val(get("receive_amount", "0"), 0.0)
        remain_qty = clean_number_val(get("remain_qty", str(receive_qty)), receive_qty)
        remain_amount = clean_number_val(get("remain_amount", str(receive_amount)), receive_amount)

        # สภาพ: normalise
        raw_cond = get("condition", "")
        if any(w in raw_cond for w in ("ปกติ", "ใช้งาน", "10")):
            condition = "ใช้งานได้ปกติ"
        elif any(w in raw_cond for w in ("ชำรุด", "เสื่อม")):
            condition = "ชำรุด"
        elif "ซ่อม" in raw_cond:
            condition = "รอซ่อม"
        elif any(w in raw_cond for w in ("จำหน่าย", "ตัดจำหน่าย")):
            condition = "จำหน่ายแล้ว"
        else:
            condition = "ใช้งานได้ปกติ"

        # วิธีได้มา: normalise
        raw_acq = get("acquire_method", "ซื้อ")
        # ตัดรหัสที่ขึ้นต้นแบบ "1 : ตกลงราคา" → เอาเฉพาะส่วนหลัง
        if ":" in raw_acq:
            raw_acq = raw_acq.split(":", 1)[-1].strip()
        acquire_method = raw_acq if raw_acq else "ซื้อ"

        item_date = _parse_thai_date(row.get(rev.get("item_date", ""), ""))

        results.append({
            "asset_no": asset_no.strip(),
            "item_name": get("item_name"),
            "item_date": item_date,
            "acquire_method": acquire_method,
            "receive_qty": receive_qty,
            "receive_amount": receive_amount,
            "lost_qty": 0,
            "remain_qty": remain_qty,
            "remain_amount": remain_amount,
            "location": get("location"),
            "condition": condition,
            "remark": get("remark"),
            "image_path": None,
        })
    return results


def tab_import():
    st.subheader("📥 นำเข้าข้อมูลจากไฟล์ Excel")
    st.caption(
        "รองรับ .xlsx / .xls ทุกรูปแบบ: ไฟล์รายงานแบบเก่า (header 2 ชั้น), "
        "ไฟล์ MIS, และไฟล์ flat table (Sheet1 / ปรับปรุง)"
    )
    uploaded_file = st.file_uploader(
        "เลือกไฟล์ Excel", type=["xlsx", "xls"], key="import_uploader"
    )
    if uploaded_file is None:
        return

    file_ext = uploaded_file.name.split(".")[-1].lower()
    engine = "openpyxl" if file_ext == "xlsx" else "xlrd"

    # ---- อ่านไฟล์ ----
    try:
        xls = pd.ExcelFile(uploaded_file, engine=engine)
    except Exception as e:
        st.error(f"❌ เปิดไฟล์ไม่ได้: {e}")
        return

    all_assets: list[dict] = []
    sheet_log: list[str] = []

    for sname in xls.sheet_names:
        if sname in _SKIP_SHEETS:
            sheet_log.append(f"⏩ ข้าม: **{sname}**")
            continue
        try:
            df = _read_sheet(xls, sname, engine)
            if df is None:
                sheet_log.append(f"⚠️ ไม่พบตารางข้อมูล: **{sname}**")
                continue
            assets = _df_to_assets(df)
            sheet_log.append(f"✅ อ่านสำเร็จ: **{sname}** ({len(assets)} รายการ)")
            all_assets.extend(assets)
        except Exception as e:
            sheet_log.append(f"❌ ผิดพลาด: **{sname}** — {e}")

    with st.expander("📋 รายละเอียดชีตที่อ่าน"):
        for log in sheet_log:
            st.markdown(log)

    if not all_assets:
        st.warning("ไม่พบข้อมูลครุภัณฑ์ที่อ่านได้จากไฟล์นี้ กรุณาตรวจสอบรูปแบบไฟล์")
        return

    # ---- ตัดซ้ำ (เลขครุภัณฑ์เดียวกัน เก็บแถวแรก) ----
    seen: set[str] = set()
    unique_assets: list[dict] = []
    for a in all_assets:
        key = a["asset_no"].strip()
        if key not in seen:
            seen.add(key)
            unique_assets.append(a)

    st.info(f"📊 พบข้อมูลทั้งหมด {len(all_assets)} รายการ → หลังกรองซ้ำเหลือ **{len(unique_assets)} รายการ**")

    # preview
    preview_df = pd.DataFrame(unique_assets).drop(columns=["image_path"], errors="ignore")
    st.dataframe(preview_df, use_container_width=True, height=300)

    if st.button("🔄 ประมวลผลและนำเข้าข้อมูล", type="primary"):
        existing = {str(a["asset_no"]).strip() for a in db.get_all_assets()}
        added, skipped, errors = 0, 0, []

        for data in unique_assets:
            asset_no = data["asset_no"]
            if asset_no in existing:
                skipped += 1
                continue
            ok, msg = db.add_asset(data, st.session_state["user"]["username"])
            if ok:
                added += 1
                existing.add(asset_no)
            else:
                errors.append(f"{asset_no}: {msg}")

        st.success(
            f"✅ นำเข้าสำเร็จ **{added}** รายการ | "
            f"⏩ ข้าม (มีในระบบแล้ว) **{skipped}** รายการ | "
            f"❌ ผิดพลาด **{len(errors)}** รายการ"
        )
        if errors:
            with st.expander("ดูรายการที่ผิดพลาด"):
                for e in errors:
                    st.write(e)

# ---------------------------------------------------------------------------
# แท็บ: จัดการผู้ใช้ (admin เท่านั้น)
# ---------------------------------------------------------------------------
def tab_users():
    st.subheader("👥 จัดการผู้ใช้งานระบบ")

    st.markdown("##### เพิ่มผู้ใช้ใหม่")
    col1, col2 = st.columns(2)
    with col1:
        new_username = st.text_input("ชื่อผู้ใช้ (username)")
        new_fullname = st.text_input("ชื่อ-สกุล")
    with col2:
        new_password = st.text_input("รหัสผ่านเริ่มต้น", type="password")
        new_role = st.selectbox("สิทธิ์การใช้งาน", ["user", "admin"],
                                 format_func=lambda r: "ผู้ใช้งานทั่วไป (ดูอย่างเดียว)" if r == "user" else "ผู้ดูแลระบบ (แก้ไขได้)")
    if st.button("➕ เพิ่มผู้ใช้", type="primary"):
        ok, msg = db.create_user(new_username, new_password, new_fullname, new_role)
        if ok:
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)

    st.divider()
    st.markdown("##### รายชื่อผู้ใช้ทั้งหมด")
    users = db.list_users()
    for u in users:
        c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
        c1.write(f"**{u['username']}**")
        c2.write(u["full_name"] or "-")
        c3.write("👑 Admin" if u["role"] == "admin" else "👤 User")
        with c4:
            if u["username"] != "admin":
                if st.button("🗑️ ลบ", key=f"deluser_{u['id']}"):
                    ok, msg = db.delete_user(u["username"])
                    st.success(msg) if ok else st.error(msg)
                    st.rerun()


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    if "user" not in st.session_state:
        login_page()
        return

    logout_button()
    is_admin = st.session_state["user"]["role"] == "admin"

    st.title("🗂️ ระบบจัดการครุภัณฑ์")
    st.caption("เชื่อมต่อฐานข้อมูล SQLite พร้อมระบบล็อคอินและรูปภาพประกอบ")

    if is_admin:
        tabs = st.tabs(["➕ เพิ่มข้อมูล", "🔍 ค้นหา / ดูข้อมูล", "📥 นำเข้าจาก Excel", "👥 จัดการผู้ใช้"])
        with tabs[0]:
            tab_add()
        with tabs[1]:
            tab_view(is_admin=True)
        with tabs[2]:
            tab_import()
        with tabs[3]:
            tab_users()
    else:
        st.info("โหมดผู้ใช้งานทั่วไป: ดูข้อมูลได้อย่างเดียว (แก้ไข/เพิ่ม/ลบ ต้องใช้บัญชีผู้ดูแลระบบ)")
        tab_view(is_admin=False)


if __name__ == "__main__":
    main()