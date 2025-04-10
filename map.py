# save as: map_with_filter.py

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# Atur layout agar full screen
st.set_page_config(page_title="Peta Lokasi Penyebaran", layout="wide")

# ⏳ Cache loading data
@st.cache_data
def load_data():
    df = pd.read_excel("LongLat_Geocode_Smartfren.xlsx")
    df.columns = df.columns.str.strip()
    return df

df = load_data()

# Validasi kolom
required_columns = {"KABUPATEN/KOTA", "Latitude", "Longitude", "KCP"}
if not required_columns.issubset(df.columns):
    st.error(f"Kolom berikut wajib ada di file: {', '.join(required_columns)}")
    st.stop()

# Sidebar - filter lokasi
st.sidebar.title("Filter Lokasi")
kabupaten_kota_list = sorted(df["KABUPATEN/KOTA"].dropna().unique().tolist())

# Session state untuk reset filter
if "selected_kabupaten" not in st.session_state:
    st.session_state.selected_kabupaten = []

if "selected_kcp" not in st.session_state:
    st.session_state.selected_kcp = []

# Tombol reset filter
if st.sidebar.button("🔄 Reset Semua Filter"):
    st.session_state.selected_kabupaten = []
    st.session_state.selected_kcp = []

# Pilih kabupaten/kota
kabupaten_kota_terpilih = st.sidebar.multiselect(
    "Pilih Kabupaten/Kota",
    kabupaten_kota_list,
    default=st.session_state.selected_kabupaten,
    placeholder="Cari atau pilih kabupaten/kota...",
    key="selected_kabupaten"
)

# Ambil list KCP berdasarkan kabupaten terpilih
filtered_for_kcp = df[df["KABUPATEN/KOTA"].isin(kabupaten_kota_terpilih)] if kabupaten_kota_terpilih else pd.DataFrame(columns=df.columns)
kcp_list = sorted(filtered_for_kcp["KCP"].dropna().unique().tolist())

# Pilih KCP
kcp_terpilih = st.sidebar.multiselect(
    "Pilih Nama KCP",
    kcp_list,
    default=st.session_state.selected_kcp,
    placeholder="Cari atau pilih KCP...",
    key="selected_kcp"
)

# ❗ Filter data akhir (dilakukan hanya jika user memilih sesuatu)
filtered_df = df.copy()

# Jika user sudah memilih kabupaten/kota atau KCP
if kabupaten_kota_terpilih or kcp_terpilih:
    if kabupaten_kota_terpilih:
        filtered_df = filtered_df[filtered_df["KABUPATEN/KOTA"].isin(kabupaten_kota_terpilih)]
    if kcp_terpilih:
        filtered_df = filtered_df[filtered_df["KCP"].isin(kcp_terpilih)]
else:
    filtered_df = pd.DataFrame(columns=df.columns)  # Peta kosong dulu

# Tentukan center peta
if not filtered_df.empty:
    lat_center = filtered_df["Latitude"].mean()
    lon_center = filtered_df["Longitude"].mean()
else:
    lat_center = 0.8500
    lon_center = 114.1500

# Buat peta
m = folium.Map(location=[lat_center, lon_center], zoom_start=6, tiles="OpenStreetMap")

# Tambahkan marker hanya kalau data terfilter tidak kosong
if not filtered_df.empty:
    for _, row in filtered_df.iterrows():
        lat, lon = row["Latitude"], row["Longitude"]
        popup_info = f"{row['KCP']}<br>{row['KABUPATEN/KOTA']}"
        folium.Marker(
            location=[lat, lon],
            popup=popup_info,
            icon=folium.Icon(color="blue", icon="info-sign"),
        ).add_to(m)

# Tampilkan di Streamlit
st.title("Peta Lokasi Penyebaran")
st.markdown("Gunakan filter di sidebar untuk memilih kabupaten/kota dan/atau nama KCP.")

st_folium(m, use_container_width=True, height=700)

