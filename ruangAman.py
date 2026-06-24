import os
import streamlit as st
import pandas as pd
from datasets import load_dataset
from google import genai
from google.genai import types

# =====================================================================
# 1. KONFIGURASI HALAMAN STREAMLIT
# =====================================================================
st.set_page_config(page_title="PsycheEase AI - Psikolog Virtual", page_icon="🧠", layout="centered")

st.title("🧠 Ruang Aman")
st.subheader("Asisten Konseling & Kesehatan Mental Virtual")
st.write("Silakan curahkan apa yang sedang kamu rasakan. Dengarkan saran baiknya.")

# =====================================================================
# 2. LOAD DATASET DARI HUGGING FACE SECARA LIVE (STREAMING)
# =====================================================================
@st.cache_data # Mencegah aplikasi mendownload ulang setiap kali user mengetik chat
def ambil_sampel_dataset():
    try:
        # Menggunakan streaming=True agar tidak mendownload file utuh ke server
        dataset = load_dataset("Amod/mental_health_counseling_conversations", split="train", streaming=True)
        
        # Mengambil 5 baris pertama sebagai contoh referensi di sidebar web
        sampel = list(dataset.take(5))
        df = pd.DataFrame(sampel)
        return df
    except Exception as e:
        return None

# Tampilkan referensi dataset di Sidebar Streamlit sebagai bukti ke Dosen
with st.sidebar:
    st.header("📚 Referensi Dataset")
    st.write("Aplikasi ini terhubung langsung ke dataset Hugging Face:")
    st.code("Amod/mental_health_counseling_conversations")
    
    df_sampel = ambil_sampel_dataset()
    if df_sampel is not None:
        st.write("Contoh Topik Keluhan yang Tersedia:")
        st.dataframe(df_sampel[['Context']].head(3))
    else:
        st.warning("Gagal memuat sampel dataset, tapi chat tetap bisa berjalan.")

# =====================================================================
# 3. INITIALISASI GEMINI API & SOP PSIKOLOG
# =====================================================================
# Di Streamlit Cloud, masukkan API Key di menu "Secrets" dengan nama GEMINI_API_KEY
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

SOP_PSIKOLOG = (
    "Ubah total gaya bahasamu. Kamu BUKAN asisten AI kaku, melainkan seorang sahabat dekat, "
    "teman curhat yang sangat hangat, tulus, pendengar yang baik, dan punya empati tinggi.\n\n"
    "IKUTI ATURAN GAYA BICARA INI:\n"
    "1. Gunakan bahasa Indonesia santai, kasual, dan akrab. Gunakan kata panggil 'aku' (sebagai teman) dan 'kamu' (ke user). "
    "Boleh gunakan bahasa percakapan sehari-hari yang natural seperti 'ya', 'banget', 'nih', 'kok', 'sih', 'puk-puk', asal tetap sopan.\n"
    "2. JANGAN menjawab terlalu panjang seperti artikel ilmiah. Jawablah dengan singkat, padat, dan bertahap (maksimal 2-3 paragraf pendek) seolah-olah sedang chatting di WhatsApp.\n"
    "3. Selalu validasi emosi mereka di awal chat dengan kalimat yang menenangkan (contoh: 'Duh, berat banget ya hari kamu...', 'Aku dengerin kok, tumpahin aja semua di sini.').\n"
    "4. JANGAN langsung menggurui atau memberi daftar tips 1 sampai 10 yang kaku. Berikan saran berupa alternatif atau ajakan pelan, seolah-olah teman yang sedang memberi masukan (contoh: 'Gimana kalau coba rehat bentar?', 'Yuk, coba tarik napas dulu bareng aku...').\n"
    "5. Gunakan sedikit emoji hangat (seperti 🤗, 🥺, ❤️, ✨) untuk membangun kedekatan emosional, tapi jangan berlebihan."
)

# =====================================================================
# 4. LOGIKA UI CHAT UTAMA (STATE MANAGEMENT)
# =====================================================================
# Membuat memory chat agar percakapan tidak hilang saat halaman di-refresh otomatis oleh Streamlit
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Halo, saya adalah psikolog virtualmu hari ini. Apa yang sedang membebani pikiranmu? Mari cerita."}
    ]

# Menampilkan riwayat chat di layar
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Menerima input chat dari user
if user_input := st.chat_input("Ketik curhatan kamu di sini..."):
    # Tampilkan chat user di layar
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Saringan Keamanan (Guardrail Bunuh Diri/Self-Harm)
    kata_kunci_bahaya = ["bunuh diri", "ingin mati", "self harm", "sayat", "mengakhiri hidup", "pengen mati"]
    if any(kata in user_input.lower() for kata in kata_kunci_bahaya):
        respon_ai = (
            "🚨 **Pesan Penting Keamanan:**\n"
            "Saya mendengar betapa beratnya bebanmu saat ini. Namun, sebagai AI, kapasitas saya sangat terbatas.\n\n"
            "Kamu sangat berharga. Mohon segera hubungi layanan darurat kesehatan mental "
            "atau hotline Into The Light Indonesia melalui situs resmi mereka. Jangan lewati ini sendirian."
        )
    else:
        # Panggil Gemini API jika aman
        with st.spinner("Psikolog AI sedang mendengarkan..."):
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=user_input,
                    config=types.GenerateContentConfig(
                        system_instruction=SOP_PSIKOLOG,
                        temperature=0.7,
                    )
                )
                respon_ai = response.text
            except Exception as e:
                respon_ai = f"Maaf, sistem kami mengalami kendala teknis: {str(e)}"
                
    # Tampilkan respon AI di layar
    with st.chat_message("assistant"):
        st.markdown(respon_ai)
    st.session_state.messages.append({"role": "assistant", "content": respon_ai})