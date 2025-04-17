import streamlit as st
import pdfplumber
import pandas as pd
import re

st.title("Verifikasi Mutasi Rekening")
st.write("Upload file PDF mutasi rekening untuk cek keaslian berdasarkan format & saldo.")

uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])

def extract_transactions(file):
    data = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            lines = page.extract_text().split("\n")
            for line in lines:
                match = re.match(r"(\d{2}/\d{2})\s+(.+?)\s+([\d.,]+)?\s*(DB|CR)?\s+([\d.,]+)?", line)
                if match:
                    tgl, ket, nominal, tipe, saldo = match.groups()
                    nominal = float(nominal.replace(".", "").replace(",", "")) if nominal else 0
                    saldo = float(saldo.replace(".", "").replace(",", "")) if saldo else None
                    data.append({
                        "Tanggal": tgl,
                        "Keterangan": ket.strip(),
                        "Nominal": nominal,
                        "Tipe": tipe,
                        "Saldo": saldo
                    })
    return pd.DataFrame(data)

def cek_saldo(df):
    df = df.dropna(subset=["Saldo"]).reset_index(drop=True)
    hasil = []
    for i in range(1, len(df)):
        prev_saldo = df.loc[i - 1, "Saldo"]
        curr = df.loc[i]
        nominal = curr["Nominal"]
        tipe = curr["Tipe"]
        expected = prev_saldo + nominal if tipe == "CR" else prev_saldo - nominal
        if abs(expected - curr["Saldo"]) > 1:
            hasil.append({
                "Tanggal": curr["Tanggal"],
                "Keterangan": curr["Keterangan"],
                "Expected": expected,
                "Actual": curr["Saldo"]
            })
    return hasil

if uploaded_file:
    st.success("File berhasil diupload!")
    df = extract_transactions(uploaded_file)
    
    if not df.empty:
        st.subheader("Transaksi Terbaca")
        st.dataframe(df.head(10))
        
        hasil = cek_saldo(df)
        st.subheader("Hasil Validasi Saldo")

        if hasil:
            st.warning(f"Ditemukan {len(hasil)} ketidaksesuaian!")
            st.dataframe(pd.DataFrame(hasil))
        else:
            st.success("Semua transaksi konsisten dan valid!")
    else:
        st.error("Tidak bisa membaca transaksi dari file ini.")
