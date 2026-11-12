from datetime import datetime
import json
import os
import streamlit as st
import requests

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

# --- Cấu hình Telegram (Có thể lấy từ st.secrets hoặc cấu hình trực tiếp) ---
# Nếu đưa lên Streamlit Cloud, anh có thể cấu hình ở phần Secrets trên giao diện web của Streamlit
TELEGRAM_TOKEN = st.secrets.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "")

# --- Giao diện bên Sidebar: Thêm mới mục bản quyền ---
st.sidebar.header("➕ Thêm Bản Quyền Mới")
with st.sidebar.form("add_license_form"):
  name_input = st.text_input("Tên thiết bị / phần mềm")
  start_date = st.date_input("Ngày bắt đầu sử dụng", value=datetime.today())
  end_date = st.date_input("Ngày hết hạn", value=datetime.today())

  submit_btn = st.form_submit_button("Thêm mới")

  if submit_btn:
    if not name_input.strip():
      st.sidebar.error("Vui lòng nhập tên thiết bị hoặc phần mềm!")
    elif end_date < start_date:
      st.sidebar.error("Ngày hết hạn không thể trước ngày bắt đầu!")
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
  st.info("Chưa có dữ liệu bản quyền nào. Hãy thêm mới ở thanh bên trái (Sidebar).")
else:
  today = datetime.now().date()
  warning_list = []

  # Chuẩn bị dữ liệu hiển thị bảng
  display_data = []
  for idx, item in enumerate(licenses):
    e_date = datetime.strptime(item["end_date"], "%Y-%m-%d").date()
    delta = (e_date - today).days

    if delta < 0:
      status_text = f"🚨 Đã quá hạn {abs(delta)} ngày!"
      tag = "🔴 HẾT HẠN"
    elif delta <= 30:
      status_text = f"⚠️ Sắp hết hạn (Còn {delta} ngày)"
      tag = "🟠 SẮP HẾT HẠN"
    else:
      status_text = f"✅ Còn hạn ({delta} ngày)"
      tag = "🟢 BÌNH THƯỜNG"

    display_data.append({
        "ID": idx,
        "Tên Thiết Bị / Phần Mềm": item["name"],
        "Ngày Bắt Đầu": item["start_date"],
        "Ngày Hết Hạn": item["end_date"],
        "Trạng Thái": status_text,
    })

    if delta <= 30:
      warning_list.append(
          f"- {item['name']}: Còn {delta} ngày (Hết hạn: {item['end_date']})"
      )

  # Hiển thị bảng
  for item in display_data:
    col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 3, 1])
    with col1:
      # Tô màu đỏ nếu sắp hết hạn hoặc quá hạn trực tiếp trên giao diện
      if "Đã quá hạn" in item["Trạng Thái"] or "Sắp hết hạn" in item["Trạng Thái"]:
        st.markdown(f"🔴 **{item['Tên Thiết Bị / Phần Mềm']}**")
      else:
        st.markdown(f"**{item['Tên Thiết Bị / Phần Mềm']}**")
    with col2:
      st.text(item["Ngày Bắt Đầu"])
    with col3:
      st.text(item["Ngày Hết Hạn"])
    with col4:
      st.text(item["Trạng Thái"])
    with col5:
      if st.button("Xóa", key=f"del_{item['ID']}"):
        del licenses[item["ID"]]
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
