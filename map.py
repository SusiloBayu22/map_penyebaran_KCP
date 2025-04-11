# save as: map_with_filter.py

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium import plugins
from io import BytesIO
import json
import os

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

warna_file = "kcp_colors.json"

def load_kcp_colors():
    if os.path.exists(warna_file):
        with open(warna_file, "r") as f:
            return json.load(f)
    return {}

def save_kcp_colors(colors_dict):
    with open(warna_file, "w") as f:
        json.dump(colors_dict, f)

if "kcp_colors" not in st.session_state:
    st.session_state.kcp_colors = load_kcp_colors()

# --- Sidebar ---
st.sidebar.title("Filter Lokasi")
provinsi_list = sorted(df["PROVINSI"].dropna().unique().tolist())
all_provinsi = st.sidebar.checkbox("Pilih Semua Provinsi", value=True)
provinsi_terpilih = provinsi_list if all_provinsi else st.sidebar.multiselect(
    "Pilih Provinsi", provinsi_list, placeholder="Cari atau pilih provinsi..."
)
filtered_by_provinsi = df[df["PROVINSI"].isin(provinsi_terpilih)] if provinsi_terpilih else pd.DataFrame(columns=df.columns)

if provinsi_terpilih:
    st.sidebar.markdown(f"### ℹ️ Info Provinsi")
    st.sidebar.markdown(f"- Terpilih: **{', '.join(provinsi_terpilih)}**")
    total_kabupaten = filtered_by_provinsi["KABUPATEN/KOTA"].nunique()
    total_titik = len(filtered_by_provinsi)
    st.sidebar.markdown(f"- Jumlah Kabupaten/Kota: **{total_kabupaten}**")
    st.sidebar.markdown(f"- Total Titik KCP: **{total_titik}**")
    kab_stat = filtered_by_provinsi.groupby("KABUPATEN/KOTA").size().sort_values(ascending=False)
    st.sidebar.markdown("#### Titik per Kabupaten/Kota:")
    for kab, count in kab_stat.items():
        st.sidebar.markdown(f"- {kab}: {count} titik")

kabupaten_list = sorted(filtered_by_provinsi["KABUPATEN/KOTA"].dropna().unique().tolist())
all_kabupaten = st.sidebar.checkbox("Pilih Semua Kabupaten/Kota", value=True)
kabupaten_terpilih = kabupaten_list if all_kabupaten else st.sidebar.multiselect(
    "Pilih Kabupaten/Kota", kabupaten_list, placeholder="Cari atau pilih kabupaten/kota..."
)

filtered_by_kabupaten = filtered_by_provinsi[filtered_by_provinsi["KABUPATEN/KOTA"].isin(kabupaten_terpilih)] if kabupaten_terpilih else pd.DataFrame(columns=df.columns)

# KCP
kcp_list = sorted(filtered_by_kabupaten["KCP"].dropna().unique().tolist())
kcp_terpilih = st.sidebar.multiselect("Pilih Nama KCP", kcp_list, placeholder="Cari atau pilih KCP...")

warna_marker = st.sidebar.selectbox("Pilih Warna Untuk KCP Spesial", ["red", "green", "blue", "orange", "purple", "darkred", "cadetblue"])

if st.sidebar.button("🎯 Tandai KCP dengan Warna Ini"):
    for kcp in kcp_terpilih:
        st.session_state.kcp_colors[kcp] = warna_marker
    save_kcp_colors(st.session_state.kcp_colors)

if st.sidebar.button("🔄 Reset Semua Warna KCP"):
    st.session_state.kcp_colors = {}
    save_kcp_colors(st.session_state.kcp_colors)

warna_shape = st.sidebar.selectbox("Pilih Warna Shape", ["red", "green", "blue", "orange", "purple", "black", "gray"])

# Map data
filtered_df = filtered_by_kabupaten.copy()
lat_center = filtered_df["Latitude"].mean() if not filtered_df.empty else 0.85
lon_center = filtered_df["Longitude"].mean() if not filtered_df.empty else 114.15

m = folium.Map(location=[lat_center, lon_center], zoom_start=6, tiles="OpenStreetMap")

# Tambahkan fitur Draw
draw = plugins.Draw(
    export=True,
    filename="data.geojson",
    draw_options={
        "polyline": {"shapeOptions": {"color": warna_shape}},
        "polygon": {"shapeOptions": {"color": warna_shape}},
        "rectangle": {"shapeOptions": {"color": warna_shape}},
        "circle": {"shapeOptions": {"color": warna_shape}},
        "marker": False,
        "circlemarker": False,
    },
    edit_options={"edit": True, "remove": True}
)
draw.add_to(m)

# Tambahkan style dan skrip tooltip untuk pengukuran
m.get_root().html.add_child(folium.Element("""
<style>
.label-style {
    background-color: white;
    color: black;
    padding: 2px 4px;
    border: 1px solid gray;
    border-radius: 3px;
    font-size: 12px;
    font-weight: bold;
}
</style>

<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet.geometryutil/0.10.0/leaflet.geometryutil.min.js"></script>

<script>
function getDistanceInKm(latlngs) {
    let total = 0;
    for (let i = 1; i < latlngs.length; i++) {
        total += latlngs[i - 1].distanceTo(latlngs[i]);
    }
    return total / 1000;
}

function getAreaInSqKm(latlngs) {
    return L.GeometryUtil.geodesicArea(latlngs) / 1e6;
}

map.on('draw:created', function (e) {
    const layer = e.layer;
    let label = "";

    if (e.layerType === 'polyline') {
        const latlngs = layer.getLatLngs();
        const distance = getDistanceInKm(latlngs).toFixed(2);
        label = "📏 Panjang: " + distance + " km";
    }

    if (e.layerType === 'polygon') {
        const latlngs = layer.getLatLngs()[0];
        const area = getAreaInSqKm(latlngs).toFixed(2);
        label = "📐 Luas: " + area + " km²";
    }

    if (e.layerType === 'circle') {
        const radius = layer.getRadius() / 1000;
        label = "⚪ Radius: " + radius.toFixed(2) + " km";
    }

    if (label !== "") {
        layer.bindTooltip(label, { permanent: true, direction: 'center', className: 'label-style' }).openTooltip();
    }

    layer.addTo(map);
});
</script>
"""))

# Tambahkan marker
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

# Tampilkan di Streamlit
st.title("🗺️ Peta Lokasi Penyebaran")
st.markdown("""
Gunakan filter di sidebar untuk memilih provinsi, kabupaten/kota, dan KCP.  
Tandai titik spesial dengan warna berbeda.  
Gunakan alat di pojok kiri atas peta untuk menggambar garis (ukur jarak), polygon (ukur luas), atau lingkaran (radius).
""")

st_data = st_folium(m, use_container_width=True, height=700)

# Download data yang difilter
buffer_all = BytesIO()
filtered_df.to_excel(buffer_all, index=False, engine='openpyxl')
buffer_all.seek(0)
st.download_button(
    label="⬇️ Download Data yang Difilter (Excel)",
    data=buffer_all,
    file_name="filtered_data.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# Download hanya KCP yang ditandai warna
kcp_colored_df = df[df["KCP"].isin(st.session_state.kcp_colors.keys())].copy()
if not kcp_colored_df.empty:
    kcp_colored_df["Warna"] = kcp_colored_df["KCP"].map(st.session_state.kcp_colors)
    buffer_colored = BytesIO()
    kcp_colored_df.to_excel(buffer_colored, index=False, engine='openpyxl')
    buffer_colored.seek(0)

    # Buat nama file berdasarkan gabungan kabupaten terpilih
    if kabupaten_terpilih:
        nama_kab = "_".join([k.lower().replace(" ", "_") for k in kabupaten_terpilih])
    else:
        nama_kab = "semua_kabupaten"
    nama_file_kcp = f"kcp_ditandai_{nama_kab}.xlsx"

    st.download_button(
        label="🎨 Download KCP yang Ditandai Saja (Excel)",
        data=buffer_colored,
        file_name=nama_file_kcp,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )




