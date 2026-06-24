import os
import random
import re
import pandas as pd
import streamlit as st
from google import genai
from google.genai import types

# ==========================================
# 1. STREAMLIT PAGE CONFIGURATION
# ==========================================
st.set_page_config(page_title="Ruang Aman - AI Companion", page_icon="🌿", layout="centered")

# ==========================================
# 2. VIRTUAL PAGE ROUTING
# ==========================================
if "halaman_saat_ini" not in st.session_state:
    st.session_state.halaman_saat_ini = "tos"

# ==========================================
# 3. INITIALIZE GEMINI CLIENT & DATASET
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
# 4. LOGIC & FUNCTIONS (SOP & Guardrail & RAG)
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
    kata_kunci_darurat = [
        # Indonesia
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
            "🚨 **Important Safety Message:**\n"
            "I can hear how heavy things are for you right now. However, as an AI, my capacity to assist in emergencies is limited. "
            "Your life is incredibly valuable. Please do not go through this alone. Reach out to local emergency services, "
            "contact a crisis hotline immediately, or visit the nearest emergency room. You are not alone. 🌿"
        )
    return None

def cari_referensi_dataset(teks_pasien: str) -> str:
    if df_dataset is None or df_dataset.empty:
        return "No database reference available."

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
        return "No database reference available."

    kata_kunci_pencarian = [kamus_keyword.get(kata, kata) for kata in kata_kunci_user if len(kamus_keyword.get(kata, kata)) > 3]

    if not kata_kunci_pencarian:
        return df_dataset.iloc[random.randint(0, len(df_dataset)-1)]['Response']

    pola_pencarian = '|'.join(kata_kunci_pencarian[:4])
    matches = df_dataset[df_dataset['Context'].str.lower().str.contains(pola_pencarian, na=False, regex=True)]

    if not matches.empty:
        return matches.iloc[0]['Response']
    else:
        return df_dataset.iloc[random.randint(0, len(df_dataset)-1)]['Response']

# ==========================================
# 5. PAGE: TERMS OF SERVICE (ToS)
# ==========================================
if st.session_state.halaman_saat_ini == "tos":
    st.title("🌿 Welcome to Ruang Aman")
    st.markdown("### Terms of Service")
    
    with st.container(border=True):
        st.markdown("""
        **Please read carefully before you start sharing:**

        1. **Not a Replacement for Professional Help:** This AI acts as a virtual companion, not a professional clinical psychologist or therapist. If you need medical or psychiatric advice, please consult a professional.
        2. **Privacy & Data:** We **do not store** your chat history on our servers. Once this tab or browser is closed, your session history is permanently wiped.
        3. **API Usage:** This chatbot is powered by the **Google Gemini API**. Consequently, your inputs are processed securely through Google's infrastructure. To protect your privacy, please do not share highly sensitive personal information (such as ID numbers, addresses, or financial data).
        4. **Safety Guardrails:** This AI includes automated keyword detection for crisis situations to guide you toward official help channels if required.
        """)
        
        if st.button("📖 Read User Guide"):
            st.session_state.halaman_saat_ini = "panduan"
            st.rerun()

    st.write("---")
    if st.button("✅ I Understand and Agree to Proceed", type="primary"):
        st.session_state.halaman_saat_ini = "chat"
        st.rerun()

# ==========================================
# 6. PAGE: USER GUIDE
# ==========================================
elif st.session_state.halaman_saat_ini == "panduan":
    st.title("📖 Ruang Aman AI - User Guide")
    
    st.markdown("""
    ### How to Get the Most Out of This Chatbot:
    
    **1. Start Sharing Your Thoughts**
    Type whatever is on your mind in the chat input. You can use casual Indonesian, English, or a mix of both. Our AI will automatically adapt to your chosen language.

    **2. Keep Personal Information Safe**
    To preserve your privacy, avoid mentioning explicit details like your full name, phone number, exact address, or credentials. Share your emotions and general situations instead.

    **3. Request Solutions Explicitly**
    If you just want someone to listen, simply vent out and the AI will act as an empathetic listener. If you explicitly need actionable steps or advice, make sure to ask questions like, *"What should I do?"* or *"Give me some advice."*

    **4. Clearing History**
    If you are on a public device or want instant privacy, click the **"Clear Chat History"** button on the left sidebar, or simply close your browser tab.
    """)
    
    st.write("---")
    if st.button("⬅️ Back to Main Page"):
        st.session_state.halaman_saat_ini = "tos"
        st.rerun()

# ==========================================
# 7. PAGE: MAIN CHAT INTERFACE
# ==========================================
elif st.session_state.halaman_saat_ini == "chat":
    st.title("🌿 Ruang Aman AI")
    st.caption("A supportive companion that is safe, empathetic, and protects your privacy.")
    
    if st.sidebar.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

    if "messages" not in st.session_state:
        st.session_state.messages = []
        st.session_state.messages.append({"role": "model", "content": "Hi there! I'm here to listen to your story. Is there anything weighing on your heart today?"})

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Type your message here..."):
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        pesan_darurat = cek_kondisi_darurat(prompt)
        
        if pesan_darurat:
            with st.chat_message("model"):
                st.markdown(pesan_darurat)
            st.session_state.messages.append({"role": "model", "content": pesan_darurat})
        else:
            with st.chat_message("model"):
                message_placeholder = st.empty()
                message_placeholder.markdown("*(Ruang Aman is typing...)*")
                
                try:
                    # 1. RAG (Smart Keyword Function)
                    referensi_medis = cari_referensi_dataset(prompt)
                    
                    # 2. Compile payload
                    contents_payload = []
                    for msg in st.session_state.messages[:-1]:
                        role = "user" if msg["role"] == "user" else "model"
                        contents_payload.append(types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])]))
                    
                    # 3. Add context
                    prompt_dengan_konteks = f"REFERENSI KASUS NYATA (Data Lokal):\n{referensi_medis}\n\nCURHATAN PASIEN SEKARANG:\n{prompt}"
                    contents_payload.append(types.Content(role="user", parts=[types.Part.from_text(text=prompt_dengan_konteks)]))
                    
                    # 4. Call Gemini
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=contents_payload,
                        config=types.GenerateContentConfig(system_instruction=SOP_PSIKOLOG, temperature=0.78, max_output_tokens=2500)
                    )
                    
                    # 5. Display response
                    message_placeholder.markdown(response.text)
                    st.session_state.messages.append({"role": "model", "content": response.text})
                    
                except Exception as e:
                    pesan_error = str(e)
                    if "429" in pesan_error or "RESOURCE_EXHAUSTED" in pesan_error:
                        error_teks = "Ouch, I'm really sorry... My brain just needs a breather because Google's servers are limited. Can you give me a break of about 1 minute? ⏳"
                    else:
                        error_teks = f"An unexpected technical glitch occurred. Please try again. Error: {pesan_error}"
                    
                    message_placeholder.markdown(error_teks)
                    st.session_state.messages.append({"role": "model", "content": error_teks})
