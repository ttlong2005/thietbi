from datetime import datetime
import json
import os
import requests
import streamlit as st

DATA_FILE = "licenses_data.json"

st.set_page_config(
    page_title="Quản lý Hạn Bản Quyền", page_icon="🛡️", layout="wide"
)

st.title("🛡️ Quản lý Hạn Bản Quyền Thiết Bị & Phần Mềm")
st.markdown(
    "Ứng dụng giúp theo dõi thời hạn bản quyền, **tự động tô đỏ** các mục sắp"
    " hết hạn trong vòng 30 ngày và gửi cảnh báo về Telegram."
)


# --- Hàm xử lý dữ liệu ---
def load_data():
  if os.path.exists(DATA_FILE):
    try:
      with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      return []
  return []


def save_data(data):
  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)


# Khởi tạo dữ liệu
licenses = load_data()

# --- Cấu hình Telegram ---
TELEGRAM_TOKEN = st.secrets.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "")

# --- Giao diện bên Sidebar: Thêm mới mục bản quyền ---
st.sidebar.header("➕ Thêm Bản Quyền Mới")
with st.sidebar.form("add_license_form"):
  name_input = st.text_input("Tên thiết bị / phần mềm")
  start_date = st.date_input(
      "Ngày sử dụng", value=datetime.today(), format="DD/MM/YYYY"
  )
  end_date = st.date_input(
      "Ngày hết hạn", value=datetime.today(), format="DD/MM/YYYY"
  )

  submit_btn = st.form_submit_button("Thêm mới")

  if submit_btn:
    if not name_input.strip():
      st.sidebar.error("Vui lòng nhập tên thiết bị hoặc phần mềm!")
    elif end_date < start_date:
      st.sidebar.error("Ngày hết hạn không thể trước ngày sử dụng!")
    else:
      licenses.append({
          "name": name_input.strip(),
          "start_date": start_date.strftime("%Y-%m-%d"),
          "end_date": end_date.strftime("%Y-%m-%d"),
      })
      save_data(licenses)
      st.sidebar.success(f"Đã thêm: {name_input}")
      st.rerun()

# --- Hiển thị danh sách chính ---
st.subheader("📋 Danh Sách Thiết Bị & Phần Mềm")

if not licenses:
  st.info(
      "Chưa có dữ liệu bản quyền nào. Hãy thêm mới ở thanh bên trái (Sidebar)."
  )
else:
  today = datetime.now().date()
  warning_list = []

  # --- HÀNG TIÊU ĐỀ CỘT ---
  h_col1, h_col2, h_col3, h_col4, h_col5, h_col6 = st.columns(
      [0.7, 3, 1.8, 1.8, 2.7, 1]
  )
  h_col1.markdown("**STT**")
  h_col2.markdown("**Thiết bị / Phần mềm**")
  h_col3.markdown("**Ngày sử dụng**")
  h_col4.markdown("**Ngày hết hạn**")
  h_col5.markdown("**Trạng thái**")
  h_col6.markdown("**Thao tác**")
  st.divider()

  # --- HIỂN THỊ TỪNG DÒNG DỮ LIỆU ---
  for idx, item in enumerate(licenses):
    s_date_obj = datetime.strptime(item["start_date"], "%Y-%m-%d").date()
    e_date_obj = datetime.strptime(item["end_date"], "%Y-%m-%d").date()
    delta = (e_date_obj - today).days

    # Định dạng ngày hiển thị DD/MM/YYYY
    s_date_str = s_date_obj.strftime("%d/%m/%Y")
    e_date_str = e_date_obj.strftime("%d/%m/%Y")

    is_warning = False
    if delta < 0:
      status_text = f"🚨 Đã quá hạn {abs(delta)} ngày!"
      is_warning = True
    elif delta <= 30:
      status_text = f"⚠️ Sắp hết hạn (Còn {delta} ngày)"
      is_warning = True
    else:
      status_text = f"✅ Còn hạn ({delta} ngày)"

    if delta <= 30:
      warning_list.append(
          f"- {item['name']}: Còn {delta} ngày (Hết hạn: {e_date_str})"
      )

    col1, col2, col3, col4, col5, col6 = st.columns([0.7, 3, 1.8, 1.8, 2.7, 1])

    with col1:
      st.write(f"{idx + 1}")
    with col2:
      if is_warning:
        st.markdown(f":red[🔴 **{item['name']}**]")
      else:
        st.markdown(f"**{item['name']}**")
    with col3:
      st.text(s_date_str)
    with col4:
      if is_warning:
        st.markdown(f":red[**{e_date_str}**]")
      else:
        st.text(e_date_str)
    with col5:
      if is_warning:
        st.markdown(f":red[**{status_text}**]")
      else:
        st.text(status_text)
    with col6:
      if st.button("Xóa", key=f"del_{idx}"):
        del licenses[idx]
        save_data(licenses)
        st.rerun()

  st.divider()

  # --- Khu vực gửi cảnh báo Telegram ---
  col_btn1, col_space = st.columns([2, 5])
  with col_btn1:
    if st.button("📤 Gửi Cảnh Báo Telegram Ngay"):
      if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        st.error(
            "Chưa cấu hình Telegram Token hoặc Chat ID trong Secrets của"
            " Streamlit!"
        )
      elif not warning_list:
        st.success("Không có thiết bị nào sắp hết hạn trong 30 ngày tới!")
      else:
        msg = "⚠️ **CẢNH BÁO HẠN BẢN QUYỀN** ⚠️\n\n" + "\n".join(warning_list)
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": msg,
            "parse_mode": "Markdown",
        }
        try:
          res = requests.post(url, json=payload)
          if res.status_code == 200:
            st.success("Đã gửi cảnh báo qua Telegram thành công!")
          else:
            st.error(f"Lỗi gửi Telegram: {res.text}")
        except Exception as e:
          st.error(f"Lỗi kết nối: {e}")
