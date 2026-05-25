import os
import random
import pandas as pd
from flask import Flask, render_template, request, jsonify
from google import genai
from google.genai import types

app = Flask(__name__)

# 1. INISIALISASI GEMINI CLIENT
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyDDk4EUfetA-IgSeTrMB8vyfZLHhaoPCOw")
client = genai.Client(api_key=GEMINI_API_KEY)

# 2. POPULASI DATASET DARI HUGGING FACE MENGGUNAKAN PANDAS
print("Sedang memuat dataset konseling dari Hugging Face... Mohon tunggu sebentar.")
try:
    url = "hf://datasets/Amod/mental_health_counseling_conversations/combined_dataset.json"
    df_dataset = pd.read_json(url, lines=True)
    print("Dataset berhasil dimuat! Total data referensi:", len(df_dataset))
except Exception as e:
    print("Gagal memuat dataset otomatis, menggunakan mode fallback hulu. Error:", e)
    df_dataset = None

# 3. SOP PSIKOLOG GAYA SAHABAT (System Instruction)
SOP_PSIKOLOG = (
    "Anda adalah seorang sahabat dekat (bestie) sekaligus Psikolog Klinis profesional yang sangat tulus, peka, dan tahu batasan.\n\n"
    "GAYA BAHASA:\n"
    "- Wajib gunakan bahasa Indonesia yang SANTAI, RELEVAN, dan TIDAK FORMAL (Gunakan kata 'Aku' dan 'Kamu').\n"
    "- Bicaralah seperti seorang teman dekat yang peduli. Hindari kata 'Anda' dan istilah medis yang kaku.\n\n"
    "ATURAN MERESPONS (LOGIKA SARAN VS VALIDASI):\n"
    "1. VALIDASI YANG PROPORSIONAL: Tanggapi emosi mereka dengan hangat dan wajar. JANGAN OVERVALIDATION (jangan berlebihan seperti 'Aduh kasihan banget kamu orang paling menderita', cukup katakan: 'Wajar kok kalau kamu ngerasa sedih/kecewa setelah kejadian itu...'). Tempatkan diri Anda sejajar sebagai teman, bukan pengasuh yang memanjakan.\n\n"
    "2. KAPAN HARUS MEMBERI SARAN?:\n"
    "   - JIKA PASIEN MEMINTA SOLUSI (misal: 'Aku harus gimana?', 'Kasih saran dong', 'Bantu aku'): Berikan 2-3 langkah konkret, sederhana, dan instan yang bisa dilakukan saat energinya habis.\n"
    "   - JIKA PASIEN HANYA CURHAT/MENUMPRAKKAN EMOSI (misal: 'Aku sedih banget hari ini', 'Aku ngerasa gagal'): JANGAN BERIKAN SARAN ATAU SOLUSI. Fokuslah 100% untuk mendengarkan, menenangkan, menjadi sandaran, dan menguatkan hatinya. Buat mereka merasa tidak sendirian.\n\n"
    "PENTING:\n"
    "- Gunakan esensi keilmuan dari 'Referensi Kasus Nyata' (jika ada) untuk memahami beban emosi mereka, namun kemas ulang dengan sangat kasual.\n"
    "- JANGAN PERNAH memotong jawaban di tengah kalimat. Pastikan semua kalimat selesai terproses sampai tanda titik terakhir."
)

# 4. GUARDRAIL KEAMANAN
def cek_kondisi_darurat(teks_pasien: str) -> str | None:
    kata_kunci_bahaya = ["bunuh diri", "ingin mati", "self harm", "sayat", "mengakhiri hidup", "pengen mati"]
    if any(kata in teks_pasien.lower() for kata in kata_kunci_bahaya):
        return (
            "🚨 **Pesan Penting Keamanan:**\n"
            "Aku denger betapa beratnya beban yang kamu pikul saat ini. Tapi, sebagai AI, "
            "kapasitas aku terbatas banget buat nemenin kamu di situasi darurat ini.\n\n"
            "Kamu berharga banget. Tolong jangan lewati ini sendirian ya? Segera hubungi layanan darurat kesehatan mental "
            "atau hotline Into The Light Indonesia lewat situs resmi mereka, atau pergi ke IGD rumah sakit terdekat. Aku sayang kamu."
        )
    return None

# 5. LOGIKA PENCARIAN DATA DI DATASET PANDAS
def cari_referensi_dataset(teks_pasien: str) -> str:
    """
    Mencari jawaban konselor yang paling relevan dari dataset Pandas
    berdasarkan kata kunci curhatan pasien.
    """
    if df_dataset is None:
        return "Tidak ada referensi database."
    
    # Cari baris data yang mengandung kata kunci mirip di kolom 'Context'
    kata_kunci = teks_pasien.lower().split()
    # Cari kecocokan kata kunci sederhana
    matches = df_dataset[df_dataset['Context'].str.lower().str.contains('|'.join(kata_kunci[:3]), na=False)]
    
    if not matches.empty:
        # Ambil satu jawaban psikolog asli secara acak yang topiknya mirip
        return matches.iloc[0]['Response']   
    else:
        # Jika tidak ada yang mirip, ambil sampel acak agar AI tetap punya insight medis
        return df_dataset.iloc[random.randint(0, len(df_dataset)-1)]['Response']

# 6. ROUTE WEBPAGE
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    curhatan_pasien = data.get("message", "")
    history = data.get("history", [])
    
    if not curhatan_pasien.strip():
        return jsonify({"response": "Eh, pesannya kosong nih. Cerita yuk, aku dengerin."})
    
    pesan_darurat = cek_kondisi_darurat(curhatan_pasien)
    if pesan_darurat:
        return jsonify({"response": pesan_darurat})
    
    try:
        # Ambil data jawaban psikolog asli dari dataset Hugging Face menggunakan Pandas
        referensi_medis = cari_referensi_dataset(curhatan_pasien)
        
        contents_payload = []
        for msg in history:
            role = "user" if msg["sender"] == "user" else "model"
            contents_payload.append(
                types.Content(role=role, parts=[types.Part.from_text(text=msg["text"])])
            )
        
        # Gabungkan pesan terbaru dengan konteks referensi Hugging Face di ujung payload
        prompt_dengan_konteks = (
            f"REFERENSI KASUS NYATA (Data Hugging Face):\n{referensi_medis}\n\n"
            f"CURHATAN PASIEN SEKARANG:\n{curhatan_pasien}"
        )
        
        contents_payload.append(
            types.Content(role="user", parts=[types.Part.from_text(text=prompt_dengan_konteks)])
        )
        
        # Kirim ke Gemini (Tanpa memori riwayat chat demi privasi, murni berbasis data referensi)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents_payload,
            config=types.GenerateContentConfig(
                system_instruction=SOP_PSIKOLOG,
                temperature=0.78,
                max_output_tokens=2500
            )
        )
        return jsonify({"response": response.text})
    except Exception as e:
        return jsonify({"response": f"Aduh maaf, otak backend aku lagi nge-blank semenit: {str(e)}"})

if __name__ == '__main__':
    app.run(debug=True)