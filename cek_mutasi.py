import streamlit as st
import pdfplumber
import pandas as pd
import re

st.set_page_config(page_title="Cek Mutasi Rekening", layout="wide")
st.title("🔍 Verifikasi Mutasi Rekening (e-Statement BCA)")

uploaded_file = st.file_uploader("Upload file PDF mutasi rekening (e-Statement)", type="pdf")

def clean_number(val):
    try:
        return float(val.replace(".", "").replace(",", ""))
    except:
        return None

def parse_mutasi(text):
    data = []
    saldo_sebelumnya = None
    lines = text.split("\n")
    for line in lines:
        # Cari baris mutasi dengan format TANGGAL DIAWALI dd/mm
        if re.match(r"\d{2}/\d{2}", line.strip()):
            parts = line.strip().split()
            try:
                tanggal = parts[0]
                # Temukan apakah ada "DB" atau "CR"
                if "DB" in parts:
                    idx = parts.index("DB")
                    tipe = "DB"
                elif "CR" in parts:
                    idx = parts.index("CR")
                    tipe = "CR"
                else:
                    tipe = None
                    idx = None

                # Saldo diambil setelah DB/CR, jika ada
                saldo = clean_number(parts[idx + 1]) if idx is not None and idx + 1 < len(parts) else None

                # Nominal mutasi diambil sebelum DB/CR
                nominal = clean_number(parts[idx - 1]) if idx is not None and idx - 1 >= 0 else None

                # Keterangan diambil di antara tanggal dan nominal
                keterangan = " ".join(parts[1:idx - 1]) if idx is not None else " ".join(parts[1:])

                data.append({
                    "Tanggal": tanggal,
                    "Keterangan": keterangan,
                    "Tipe": tipe,
                    "Nominal": nominal,
                    "Saldo": saldo
                })
            except:
                continue
    return pd.DataFrame(data)

def validasi_saldo(df):
    hasil = []
    prev_saldo = None
    for i, row in df.iterrows():
        if pd.notna(row["Saldo"]) and pd.notna(row["Nominal"]) and row["Tipe"]:
            if prev_saldo is not None:
                expected = prev_saldo + row["Nominal"] if row["Tipe"] == "CR" else prev_saldo - row["Nominal"]
                if abs(expected - row["Saldo"]) > 2:
                    hasil.append({
                        "Tanggal": row["Tanggal"],
                        "Keterangan": row["Keterangan"],
                        "Expected Saldo": expected,
                        "Actual Saldo": row["Saldo"]
                    })
            prev_saldo = row["Saldo"]
        elif pd.notna(row["Saldo"]):
            prev_saldo = row["Saldo"]
    return hasil

if uploaded_file:
    with pdfplumber.open(uploaded_file) as pdf:
        full_text = "\n".join(page.extract_text() for page in pdf.pages)
        df = parse_mutasi(full_text)

# --- ANALISA RINGKAS ---
st.subheader("📊 Ringkasan Mutasi")

# Total Kredit & Debet
total_kredit = df[df["Tipe"] == "CR"]["Nominal"].sum()
total_debit = df[df["Tipe"] == "DB"]["Nominal"].sum()

# Group by Tanggal -> Ambil saldo terakhir hari itu
harian = df.dropna(subset=["Saldo"]).groupby("Tanggal").agg({
    "Saldo": "last"
}).reset_index()

# Saldo Tertinggi & Terendah Harian
saldo_tertinggi = harian.loc[harian["Saldo"].idxmax()]
saldo_terendah = harian.loc[harian["Saldo"].idxmin()]

# Tampilkan
col1, col2 = st.columns(2)
with col1:
    st.metric("💰 Total Kredit", f"Rp {total_kredit:,.0f}")
    st.metric("📉 Saldo Terendah Harian", f"Rp {saldo_terendah['Saldo']:,.0f} ({saldo_terendah['Tanggal']})")
with col2:
    st.metric("💸 Total Debet", f"Rp {total_debit:,.0f}")
    st.metric("📈 Saldo Tertinggi Harian", f"Rp {saldo_tertinggi['Saldo']:,.0f} ({saldo_tertinggi['Tanggal']})")

        st.subheader("📋 Tabel Mutasi Terbaca")
        st.dataframe(df)

        st.subheader("🧪 Validasi Saldo")
        hasil = validasi_saldo(df)

        if hasil:
            st.warning(f"🚨 Ditemukan {len(hasil)} transaksi tidak konsisten.")
            st.dataframe(pd.DataFrame(hasil))
        else:
            st.success("✅ Semua saldo mutasi valid dan konsisten!")
