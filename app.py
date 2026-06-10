import os
import random
import re
import time
import pandas as pd
import streamlit as st
from google import genai
from google.genai import types

# 1. KONFIGURASI HALAMAN STREAMLIT
st.set_page_config(page_title="Ruang Aman - Psikolog AI", page_icon="🌿", layout="centered")

# PERMISSION SCREEN
if "permission_granted" not in st.session_state:
    st.session_state.permission_granted = False

if not st.session_state.permission_granted:
    st.title("🌿 Ruang Aman AI")
    st.caption("Sebelum memulai, harap baca dan setujui panduan pengguna berikut.")

    st.markdown("---")

    # ── ISI PANDUAN PENGGUNA ──
    st.subheader("📋 Panduan Pengguna")
    st.markdown(
        """
        *(Isi panduan pengguna Anda di sini. Buka file `app.py` dan cari bagian 
        bertanda **"ISI PANDUAN PENGGUNA"**, lalu ganti teks ini dengan panduan lengkap Anda.)*
        """
    )
    # ── AKHIR PANDUAN PENGGUNA ──

    st.markdown("---")

    agree = st.checkbox("Saya telah membaca panduan pengguna dan menyetujui hal-hal di dalamnya.")

    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("✅ Lanjut", disabled=not agree, use_container_width=True, type="primary"):
            st.session_state.permission_granted = True
            st.rerun()

    with col2:
        if st.button("❌ Batalkan", use_container_width=True):
            st.warning("Kamu memilih untuk tidak melanjutkan. Tutup tab ini untuk keluar.")
            st.stop()

    st.stop()  # Hentikan eksekusi sampai permission diberikan



# MAIN APP (hanya jalan setelah permission disetujui)
st.title("🌿 Ruang Aman AI")
st.caption("Sahabat curhat yang aman, empatik, dan menjaga privasimu.")


# 2. INISIALISASI GEMINI CLIENT & DATASET
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "MASUKKAN_API_KEY_CADANGAN_DISINI")
client = genai.Client(api_key=GEMINI_API_KEY)

# Gunakan cache agar Pandas tidak meload ulang dataset setiap kali user nge-chat
@st.cache_data
def load_dataset():
    try:
        file_path = "dataset/cleaned_dataset.json"
        df = pd.read_json(file_path, lines=True)
        return df
    except Exception as e:
        st.error(f"Gagal memuat dataset: {e}")
        return None

df_dataset = load_dataset()

# 3. SOP PSIKOLOG
SOP_PSIKOLOG = (
    "Anda adalah seorang sahabat dekat (bestie) sekaligus Psikolog Klinis profesional yang sangat tulus, peka, dan tahu batasan.\n\n"
    "ADAPTASI GAYA BAHASA (PENTING!):\n"
    "Sesuaikan bahasa balasan Anda dengan bahasa yang diinputkan oleh pasien:\n"
    "1. Jika input 100% Bahasa Indonesia -> Balas pakai Bahasa Indonesia yang SANTAI, RELEVAN, dan TIDAK FORMAL (Gunakan kata 'Aku' dan 'Kamu').\n"
    "2. Jika input 100% Bahasa Inggris -> Balas pakai Bahasa Inggris yang CASUAL, EMPATHETIC, dan WARM (Gunakan 'I' dan 'You', act like a close friend).\n"
    "3. Jika input Campuran (Indonesia & Inggris) -> Balas pakai Bahasa Indonesia yang SANTAI dan kasual.\n"
    "Catatan: Bicaralah seperti seorang teman dekat yang peduli. Hindari bahasa baku, kata 'Anda', dan istilah medis yang kaku.\n\n"
    "ATURAN MERESPONS (LOGIKA SARAN VS VALIDASI):\n"
    "1. VALIDASI YANG PROPORSIONAL: Tanggapi emosi mereka dengan hangat dan wajar. JANGAN OVERVALIDATION (jangan berlebihan seperti 'Aduh kasihan banget kamu orang paling menderita'). Tempatkan diri Anda sejajar sebagai teman, bukan pengasuh yang memanjakan.\n\n"
    "2. KAPAN HARUS MEMBERI SARAN?:\n"
    "   - JIKA PASIEN MEMINTA SOLUSI (misal: 'Aku harus gimana?', 'What should I do?'): Berikan 2-3 langkah konkret, sederhana, dan instan yang bisa dilakukan saat energinya habis.\n"
    "   - JIKA PASIEN HANYA CURHAT/MENUMPRAKKAN EMOSI: JANGAN BERIKAN SARAN ATAU SOLUSI. Fokuslah 100% untuk mendengarkan, menenangkan, menjadi sandaran, dan menguatkan hatinya. Buat mereka merasa tidak sendirian.\n\n"
    "PENTING:\n"
    "- Gunakan esensi keilmuan dari 'Referensi Kasus Nyata' (jika ada) untuk memahami beban emosi mereka, namun kemas ulang dengan sangat kasual.\n"
    "- JANGAN PERNAH memotong jawaban di tengah kalimat. Pastikan semua kalimat selesai terproses sampai tanda titik terakhir."
)

# 4. GUARDRAIL KEAMANAN
def cek_kondisi_darurat(teks_pasien: str) -> str | None:
    kata_kunci_darurat = [
        #Indonesia
        'bunuh diri', 'bunuhdiri', 'akhiri hidup', 'mengakhiri hidup', 'cabut nyawa',
        'ingin mati', 'pengen mati', 'mau mati', 'mending mati', 'mending aku mati',
        'mati saja', 'mati aja', 'cara mati', 'biarkan aku mati', 'lebih baik mati',
        'kalau aku mati', 'dengan mati', 'dibunuh', 'tiada', 'tidur selamanya',
        'lenyap dari dunia', 'menyusul tuhan', 'selamat tinggal dunia', 'akhir dari segalanya',
        'sudah saatnya aku pergi', 'tidak hidup', 'tetap hidup', 'nyerah sama hidup',
        'capek hidup', 'gak kuat hidup', 'nggak kuat hidup', 'self harm', 'self-harm',
        'menyakiti diri', 'menyakiti diriku', 'melukai diri', 'nyilet', 'menyayat',
        'sayat', 'cutting', 'potong nadi', 'gantung diri', 'lompat', 'loncat',
        'nabrakin diri', 'menabrakkan diri', 'racun', 'baygon', 'overdosis', 'telan pil',
        'puluhan pil', 'menusuk', 'surat wasiat', 'pesan terakhir',
        
        # Inggris
        'suicide', 'kill myself', 'killing myself', 'want to die', 'end my life', 'end it all',
        'rather be dead', 'rather die', 'stop living', 'dont want to live', "don't want to live",
        'sleep forever', 'better off dead', 'take my own life', 'take my life', 'ready to die',
        'just die', 'let me die', 'if i die', 'die painlessly', 'by dying',
        'cut myself', 'cutting myself', 'cutting my', 'cut my arm', 'slit my wrists',
        'hang myself', 'swallow pills', 'poison', 'bug spray', 'jump off', 'jumping off',
        'jump from', 'about to jump', 'stab myself', 'hurt myself', 'hurting myself',
        'harm myself', 'swallow a bottle', 'dozens of pills', 'suicide note', 'done with life',
        'no reason to live', 'goodbye world', 'goodbye everyone', 'end the pain forever',
        'way out of this life', "wasn't alive", 'stay alive', 'disappear from this world',
        'throw myself', 'bear living', "i'm gone", 'be killed'
    ]

    if any(kata in teks_pasien.lower() for kata in kata_kunci_darurat):
        return (
            "🚨 **Pesan Penting Keamanan / Important Safety Message:**\n"
            "Aku denger betapa beratnya beban yang kamu pikul saat ini. Tapi, sebagai AI, "
            "kapasitas aku terbatas banget buat nemenin kamu di situasi darurat ini.\n\n"
            "Kamu berharga banget. Tolong jangan lewati ini sendirian ya? Segera hubungi layanan darurat kesehatan mental "
            "atau hotline Into The Light Indonesia lewat situs resmi mereka, atau pergi ke IGD rumah sakit terdekat. Aku sayang kamu. / *Please reach out to local emergency services or a suicide prevention hotline immediately. You are not alone.*"
        )
    return None

# 5. LOGIKA RAG PANDAS
def cari_referensi_dataset(teks_pasien: str) -> str:
    if df_dataset is None or df_dataset.empty:
        return "Tidak ada referensi database."

    kamus_keyword = {
        'tidur': 'sleep', 'depresi': 'depress', 'cemas': 'anxiety', 'panik': 'panic',
        'sedih': 'sad', 'marah': 'angry', 'takut': 'fear', 'bingung': 'confused',
        'putus': 'breakup', 'keluarga': 'family', 'teman': 'friend', 'pacar': 'boyfriend',
        'kerja': 'job', 'lelah': 'tired', 'capek': 'tired', 'stres': 'stress',
        'berguna': 'worthless', 'benci': 'hate', 'gagal': 'failure', 'nangis': 'cry',
        'trauma': 'trauma', 'insecure': 'insecure', 'overthinking': 'think', 'sendiri': 'lonely'
    }

    teks_bersih = re.sub(r'[^\w\s]', '', teks_pasien).lower()
    kata_kunci_user = teks_bersih.split()

    if not kata_kunci_user:
        return "Tidak ada referensi database."

    kata_kunci_pencarian = [kamus_keyword.get(kata, kata) for kata in kata_kunci_user if len(kamus_keyword.get(kata, kata)) > 3]

    if not kata_kunci_pencarian:
        return df_dataset.iloc[random.randint(0, len(df_dataset)-1)]['Response']

    pola_pencarian = '|'.join(kata_kunci_pencarian[:4])
    matches = df_dataset[df_dataset['Context'].str.lower().str.contains(pola_pencarian, na=False, regex=True)]

    if not matches.empty:
        return matches.iloc[0]['Response']
    else:
        return df_dataset.iloc[random.randint(0, len(df_dataset)-1)]['Response']

# 6. UI & LOGIKA CHAT STREAMLIT
# Inisialisasi history chat di session state
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Pesan sapaan awal
    st.session_state.messages.append({"role": "model", "content": "Hai! Aku di sini buat dengerin cerita kamu. Ada yang lagi mengganjal di hati hari ini?"})

# Tampilkan history obrolan
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Menerima input dari user
if prompt := st.chat_input("Ketik pesan Anda di sini..."):
    # Tampilkan pesan user di UI
    st.chat_message("user").markdown(prompt)
    # Simpan ke history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Cek Guardrail Darurat
    pesan_darurat = cek_kondisi_darurat(prompt)

    if pesan_darurat:
        with st.chat_message("model"):
            st.markdown(pesan_darurat)
        st.session_state.messages.append({"role": "model", "content": pesan_darurat})

    else:
        # Jika aman, jalankan RAG dan Gemini
        with st.chat_message("model"):
            message_placeholder = st.empty()
            message_placeholder.markdown("*(Sedang mengetik...)*")

            try:
                # 1. RAG
                referensi_medis = cari_referensi_dataset(prompt)

                # 2. Susun payload untuk Gemini
                contents_payload = []
                for msg in st.session_state.messages[:-1]:  # Ambil history kecuali pesan terakhir
                    role = "user" if msg["role"] == "user" else "model"
                    contents_payload.append(
                        types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])])
                    )

                # 3. Gabungkan pesan terbaru dengan konteks lokal
                prompt_dengan_konteks = (
                    f"REFERENSI KASUS NYATA (Data Lokal):\n{referensi_medis}\n\n"
                    f"CURHATAN PASIEN SEKARANG:\n{prompt}"
                )
                contents_payload.append(
                    types.Content(role="user", parts=[types.Part.from_text(text=prompt_dengan_konteks)])
                )

                # 4. Panggil Gemini
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=contents_payload,
                    config=types.GenerateContentConfig(
                        system_instruction=SOP_PSIKOLOG,
                        temperature=0.78,
                        max_output_tokens=2500
                    )
                )

                # 5. Tampilkan hasil
                message_placeholder.markdown(response.text)
                st.session_state.messages.append({"role": "model", "content": response.text})

            except Exception as e:
                pesan_error = str(e)
                if "429" in pesan_error or "RESOURCE_EXHAUSTED" in pesan_error:
                    error_teks = "Aduh, maaf banget ya... Otakku lagi butuh napas sebentar karena server Google limit. Boleh kasih aku waktu istirahat sekitar 1 menit? ⏳"
                else:
                    error_teks = f"Waduh, koneksi batinku lagi agak terganggu nih. Error: {pesan_error}"

                message_placeholder.markdown(error_teks)
                st.session_state.messages.append({"role": "model", "content": error_teks})