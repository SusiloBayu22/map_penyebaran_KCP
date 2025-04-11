# save as: map_with_filter.py

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from io import BytesIO

st.set_page_config(page_title="Peta Lokasi Penyebaran", layout="wide")

@st.cache_data
def load_data():
    df = pd.read_excel("LongLat_Geocode_Smartfren.xlsx")
    df.columns = df.columns.str.strip()
    return df

df = load_data()

required_columns = {"PROVINSI", "KABUPATEN/KOTA", "Latitude", "Longitude", "KCP"}
if not required_columns.issubset(df.columns):
    st.error(f"Kolom berikut wajib ada di file: {', '.join(required_columns)}")
    st.stop()

if "kcp_colors" not in st.session_state:
    st.session_state.kcp_colors = {}

# Sidebar - Filter Lokasi
st.sidebar.title("Filter Lokasi")
provinsi_list = sorted(df["PROVINSI"].dropna().unique().tolist())
all_provinsi = st.sidebar.checkbox("Pilih Semua Provinsi", value=True)

provinsi_terpilih = provinsi_list if all_provinsi else st.sidebar.multiselect(
    "Pilih Provinsi",
    provinsi_list,
    placeholder="Cari atau pilih provinsi..."
)

filtered_by_provinsi = df[df["PROVINSI"].isin(provinsi_terpilih)] if provinsi_terpilih else pd.DataFrame(columns=df.columns)

# Informasi detail
if provinsi_terpilih:
    st.sidebar.markdown(f"### ℹ️ Info Provinsi")
    st.sidebar.markdown(f"- Terpilih: **{', '.join(provinsi_terpilih)}**")
    
    total_kabupaten = filtered_by_provinsi["KABUPATEN/KOTA"].nunique()
    total_titik = len(filtered_by_provinsi)

    st.sidebar.markdown(f"- Jumlah Kabupaten/Kota: **{total_kabupaten}**")
    st.sidebar.markdown(f"- Total Titik KCP: **{total_titik}**")
    st.sidebar.markdown("#### Titik per Kabupaten/Kota:")
    
    kab_stat = (
        filtered_by_provinsi
        .groupby("KABUPATEN/KOTA")
        .size()
        .sort_values(ascending=False)
    )

    for kab, count in kab_stat.items():
        st.sidebar.markdown(f"- {kab}: {count} titik")

# Filter Kabupaten/Kota
kabupaten_list = sorted(filtered_by_provinsi["KABUPATEN/KOTA"].dropna().unique().tolist())
all_kabupaten = st.sidebar.checkbox("Pilih Semua Kabupaten/Kota", value=True)

kabupaten_terpilih = kabupaten_list if all_kabupaten else st.sidebar.multiselect(
    "Pilih Kabupaten/Kota",
    kabupaten_list,
    placeholder="Cari atau pilih kabupaten/kota..."
)

filtered_by_kabupaten = filtered_by_provinsi[filtered_by_provinsi["KABUPATEN/KOTA"].isin(kabupaten_terpilih)] if kabupaten_terpilih else pd.DataFrame(columns=df.columns)

# Filter KCP
kcp_list = sorted(filtered_by_kabupaten["KCP"].dropna().unique().tolist())
kcp_terpilih = st.sidebar.multiselect("Pilih Nama KCP", kcp_list, placeholder="Cari atau pilih KCP...")

warna_marker = st.sidebar.selectbox(
    "Pilih Warna Untuk KCP Spesial",
    ["red", "green", "blue", "orange", "purple", "darkred", "cadetblue"]
)

if st.sidebar.button("🎯 Tandai KCP dengan Warna Ini"):
    for kcp in kcp_terpilih:
        st.session_state.kcp_colors[kcp] = warna_marker

if st.sidebar.button("🔄 Reset Semua Warna KCP"):
    st.session_state.kcp_colors = {}

filtered_df = filtered_by_kabupaten.copy()

if not filtered_df.empty:
    lat_center = filtered_df["Latitude"].mean()
    lon_center = filtered_df["Longitude"].mean()
else:
    lat_center = 0.8500
    lon_center = 114.1500

m = folium.Map(location=[lat_center, lon_center], zoom_start=6, tiles="OpenStreetMap")

for _, row in filtered_df.iterrows():
    lat, lon = row["Latitude"], row["Longitude"]
    kcp = row["KCP"]
    popup_info = f"{kcp}<br>{row['KABUPATEN/KOTA']}<br>{row['PROVINSI']}"
    icon_color = st.session_state.kcp_colors.get(kcp, "blue")
    folium.Marker(
        location=[lat, lon],
        popup=popup_info,
        icon=folium.Icon(color=icon_color, icon="info-sign"),
    ).add_to(m)

st.title("🗺️ Peta Lokasi Penyebaran")
st.markdown("Gunakan filter di sidebar untuk memilih provinsi, kabupaten/kota, dan KCP. Tandai titik spesial dengan warna berbeda.")

st_folium(m, use_container_width=True, height=700)

# --- Tombol download data hasil filter ---
buffer_all = BytesIO()
filtered_df.to_excel(buffer_all, index=False, engine='openpyxl')
buffer_all.seek(0)

st.download_button(
    label="⬇️ Download Data yang Difilter (Excel)",
    data=buffer_all,
    file_name="filtered_data.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# --- Tombol download KCP yang sudah ditandai ---
kcp_colored_df = df[df["KCP"].isin(st.session_state.kcp_colors.keys())].copy()
if not kcp_colored_df.empty:
    # Tambahkan kolom warna
    kcp_colored_df["Warna"] = kcp_colored_df["KCP"].map(st.session_state.kcp_colors)

    buffer_colored = BytesIO()
    kcp_colored_df.to_excel(buffer_colored, index=False, engine='openpyxl')
    buffer_colored.seek(0)

    st.download_button(
        label="🎨 Download KCP yang Ditandai Saja (Excel)",
        data=buffer_colored,
        file_name="kcp_ditandai.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


