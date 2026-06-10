import os
import random
import re
import pandas as pd
import streamlit as st
from google import genai
from google.genai import types

# ==========================================
# 1. KONFIGURASI HALAMAN STREAMLIT
# ==========================================
st.set_page_config(page_title="Ruang Aman - Psikolog AI", page_icon="🌿", layout="centered")

# ==========================================
# 2. INISIALISASI ROUTING HALAMAN
# ==========================================
# Kita buat sistem navigasi virtual: "tos", "panduan", atau "chat"
if "halaman_saat_ini" not in st.session_state:
    st.session_state.halaman_saat_ini = "tos"

# ==========================================
# 3. INISIALISASI GEMINI CLIENT & DATASET
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") 
client = genai.Client(api_key=GEMINI_API_KEY)

@st.cache_data
def load_dataset():
    try:
        file_path = "dataset/cleaned_dataset.json"
        df = pd.read_json(file_path, lines=True)
        return df
    except Exception as e:
        return None

df_dataset = load_dataset()

# ==========================================
# 4. LOGIKA & FUNGSI (SOP & Guardrail)
# ==========================================
SOP_PSIKOLOG = (
    "Anda adalah seorang sahabat dekat (bestie) sekaligus Psikolog Klinis profesional yang sangat tulus, peka, dan tahu batasan.\n\n"
    "ADAPTASI GAYA BAHASA (PENTING!):\n"
    "Sesuaikan bahasa balasan Anda dengan bahasa yang diinputkan oleh pasien:\n"
    "1. Jika input 100% Bahasa Indonesia -> Balas pakai Bahasa Indonesia yang SANTAI, RELEVAN, dan TIDAK FORMAL (Gunakan kata 'Aku' dan 'Kamu').\n"
    "2. Jika input 100% Bahasa Inggris -> Balas pakai Bahasa Inggris yang CASUAL, EMPATHETIC, dan WARM (Gunakan 'I' dan 'You', act like a close friend).\n"
    "3. Jika input Campuran (Indonesia & Inggris) -> Balas pakai Bahasa Indonesia yang SANTAI dan kasual.\n"
    "Catatan: Bicaralah seperti seorang teman dekat yang peduli. Hindari bahasa baku, kata 'Anda', dan istilah medis yang kaku.\n\n"
    "ATURAN MERESPONS (LOGIKA SARAN VS VALIDASI):\n"
    "1. VALIDASI YANG PROPORSIONAL: Tanggapi emosi mereka dengan hangat dan wajar. JANGAN OVERVALIDATION.\n\n"
    "2. KAPAN HARUS MEMBERI SARAN?:\n"
    "   - JIKA PASIEN MEMINTA SOLUSI: Berikan 2-3 langkah konkret dan sederhana.\n"
    "   - JIKA PASIEN HANYA CURHAT: JANGAN BERIKAN SARAN. Fokuslah 100% untuk mendengarkan dan menenangkan.\n\n"
    "PENTING:\n"
    "- Gunakan esensi keilmuan dari 'Referensi Kasus Nyata' untuk memahami beban emosi mereka.\n"
    "- JANGAN PERNAH memotong jawaban di tengah kalimat."
)

def cek_kondisi_darurat(teks_pasien: str) -> str | None:
    kata_kunci_darurat = ['bunuh diri', 'ingin mati', 'self harm', 'suicide', 'kill myself', 'akhiri hidup', 'pengen mati']
    if any(kata in teks_pasien.lower() for kata in kata_kunci_darurat):
        return (
            "🚨 **Pesan Penting Keamanan:**\n"
            "Aku denger betapa beratnya beban yang kamu pikul saat ini. Tapi, sebagai AI, kapasitas aku terbatas. "
            "Kamu berharga banget. Segera hubungi hotline Into The Light Indonesia atau pergi ke IGD terdekat. Kamu tidak sendirian. 🌿"
        )
    return None

def cari_referensi_dataset(teks_pasien: str) -> str:
    if df_dataset is None or df_dataset.empty:
        return "Tidak ada referensi database."
    teks_bersih = re.sub(r'[^\w\s]', '', teks_pasien).lower()
    pola_pencarian = '|'.join(teks_bersih.split()[:4])
    try:
        matches = df_dataset[df_dataset['Context'].str.lower().str.contains(pola_pencarian, na=False, regex=True)]
        return matches.iloc[0]['Response'] if not matches.empty else df_dataset.iloc[random.randint(0, len(df_dataset)-1)]['Response']
    except:
        return "Referensi umum."


# ==========================================
# 5. HALAMAN: TERMS OF SERVICE (ToS)
# ==========================================
if st.session_state.halaman_saat_ini == "tos":
    st.title("🌿 Selamat Datang di Ruang Aman")
    st.markdown("### Syarat & Ketentuan Layanan (*Terms of Service*)")
    
    with st.container(border=True):
        st.markdown("""
        **Mohon baca sebentar sebelum kamu mulai bercerita:**

        1. **Bukan Pengganti Psikolog:** AI ini adalah teman curhat virtual, bukan ahli psikolog klinis. Jika kamu merasa butuh bantuan medis, silakan hubungi profesional.
        2. **Privasi & Data:** Kami **tidak menyimpan** riwayat chat kamu di server kami setelah tab ini ditutup.
        3. **Penggunaan API:** Chatbot ini menggunakan **API Google Gemini**. Secara tidak langsung, input yang kamu ketik akan diproses oleh sistem Google. Jangan masukkan data sensitif (KTP/PIN/Alamat).
        4. **Keamanan:** AI ini dilengkapi deteksi kondisi darurat untuk membantu mengarahkanmu ke layanan bantuan resmi jika diperlukan.
        """)
        
        # Tombol untuk pindah ke halaman Panduan Pengguna
        if st.button("📖 Baca Panduan Pengguna"):
            st.session_state.halaman_saat_ini = "panduan"
            st.rerun()

    st.write("---")
    # Tombol Persetujuan untuk lanjut ke obrolan
    if st.button("✅ Saya Mengerti dan Setuju untuk Melanjutkan", type="primary"):
        st.session_state.halaman_saat_ini = "chat"
        st.rerun()


# ==========================================
# 6. HALAMAN: PANDUAN PENGGUNA
# ==========================================
elif st.session_state.halaman_saat_ini == "panduan":
    st.title("📖 Panduan Pengguna Ruang Aman AI")
    
    st.markdown("""
    ### Cara Menggunakan Chatbot Ini dengan Maksimal:
    
    **1. Mulailah Bercerita**
    Ketikkan apa saja yang sedang kamu rasakan di kolom obrolan. Kamu bisa menggunakan Bahasa Indonesia yang santai, Bahasa Inggris, atau campuran keduanya. AI kami akan menyesuaikan gaya bahasamu.

    **2. Jangan Bagikan Informasi Pribadi**
    Untuk menjaga keamanan datamu, hindari menyebutkan nama lengkap, nomor telepon, alamat rumah, atau informasi perbankan. Ceritakan saja perasaamu atau situasi umum yang kamu hadapi.

    **3. Minta Saran Hanya Jika Perlu**
    Jika kamu hanya ingin didengarkan, ceritakan saja keluh kesahmu, dan AI akan menjadi pendengar yang baik. Namun, jika kamu butuh solusi, kamu bisa secara eksplisit bertanya, *"Aku harus gimana ya?"* atau *"Beri aku saran dong."*

    **4. Menghapus Riwayat**
    Jika kamu menggunakan perangkat umum atau ingin privasi ekstra, kamu bisa menekan tombol **"Hapus Riwayat Chat"** di bilah kiri (*sidebar*) atau cukup tutup tab browser kamu.
    """)
    
    st.write("---")
    # Tombol untuk kembali ke halaman ToS
    if st.button("⬅️ Kembali ke Halaman Utama"):
        st.session_state.halaman_saat_ini = "tos"
        st.rerun()


# ==========================================
# 7. HALAMAN: INTERFACE CHAT UTAMA
# ==========================================
elif st.session_state.halaman_saat_ini == "chat":
    st.title("🌿 Ruang Aman AI")
    st.caption("Sahabat curhat yang aman, empatik, dan menjaga privasimu.")
    
    # Tombol Reset Chat di Sidebar
    if st.sidebar.button("🗑️ Hapus Riwayat Chat"):
        st.session_state.messages = []
        st.rerun()

    # Inisialisasi history chat
    if "messages" not in st.session_state:
        st.session_state.messages = []
        st.session_state.messages.append({"role": "model", "content": "Hai! Aku di sini buat dengerin cerita kamu. Ada yang lagi mengganjal di hati hari ini?"})

    # Tampilkan history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input User
    if prompt := st.chat_input("Ketik pesan Anda di sini..."):
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Cek Guardrail
        pesan_darurat = cek_kondisi_darurat(prompt)
        
        if pesan_darurat:
            with st.chat_message("model"):
                st.markdown(pesan_darurat)
            st.session_state.messages.append({"role": "model", "content": pesan_darurat})
        else:
            with st.chat_message("model"):
                message_placeholder = st.empty()
                message_placeholder.markdown("*(Ruang Aman sedang mengetik...)*")
                
                try:
                    referensi_medis = cari_referensi_dataset(prompt)
                    contents_payload = []
                    for msg in st.session_state.messages[:-1]:
                        role = "user" if msg["role"] == "user" else "model"
                        contents_payload.append(types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])]))
                    
                    prompt_dengan_konteks = f"REFERENSI KASUS NYATA:\n{referensi_medis}\n\nCURHATAN PASIEN:\n{prompt}"
                    contents_payload.append(types.Content(role="user", parts=[types.Part.from_text(text=prompt_dengan_konteks)]))
                    
                    response = client.models.generate_content(
                        model='gemini-2.0-flash',
                        contents=contents_payload,
                        config=types.GenerateContentConfig(system_instruction=SOP_PSIKOLOG, temperature=0.78, max_output_tokens=2500)
                    )
                    
                    message_placeholder.markdown(response.text)
                    st.session_state.messages.append({"role": "model", "content": response.text})
                    
                except Exception as e:
                    pesan_error = str(e)
                    if "429" in pesan_error or "RESOURCE_EXHAUSTED" in pesan_error:
                        error_teks = "Ouch, I'm really sorry... My brain just needs a breather because Google's servers are limited. Can you give me a break of about 1 minute? ⏳"
                    else:
                        error_teks = f"Waduh, ada kendala teknis nih. Coba lagi ya? Error: {pesan_error}"
                    
                    message_placeholder.markdown(error_teks)
                    st.session_state.messages.append({"role": "model", "content": error_teks})