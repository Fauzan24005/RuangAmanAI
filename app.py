import os
import random
import re
import pandas as pd
from flask import Flask, render_template, request, jsonify
from google import genai
from google.genai import types

app = Flask(__name__)

# 1. INISIALISASI GEMINI CLIENT
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

# 2. POPULASI DATASET DARI FILE LOKAL MENGGUNAKAN PANDAS
print("Sedang memuat dataset konseling dari file lokal... Mohon tunggu sebentar.")
try:
    # Mengarah ke file hasil cleaning di dalam folder dataset
    file_path = "dataset/cleaned_dataset.json"
    df_dataset = pd.read_json(file_path, lines=True)
    print("Dataset berhasil dimuat! Total data referensi:", len(df_dataset))
except Exception as e:
    print("Gagal memuat dataset lokal. Pastikan file ada di folder yang benar. Error:", e)
    df_dataset = None

# 3. SOP PSIKOLOG GAYA SAHABAT (System Instruction)
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
    kata_kunci_bahaya = ["bunuh diri", "ingin mati", "self harm", "sayat", "mengakhiri hidup", "pengen mati", "suicide", "kill myself", "want to die"]
    if any(kata in teks_pasien.lower() for kata in kata_kunci_bahaya):
        return (
            "🚨 **Pesan Penting Keamanan / Important Safety Message:**\n"
            "Aku denger betapa beratnya beban yang kamu pikul saat ini. Tapi, sebagai AI, "
            "kapasitas aku terbatas banget buat nemenin kamu di situasi darurat ini.\n\n"
            "Kamu berharga banget. Tolong jangan lewati ini sendirian ya? Segera hubungi layanan darurat kesehatan mental "
            "atau hotline Into The Light Indonesia lewat situs resmi mereka, atau pergi ke IGD rumah sakit terdekat. Aku sayang kamu. / *Please reach out to local emergency services or a suicide prevention hotline immediately. You are not alone.*"
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
    
    # Bersihkan tanda baca dan ambil 3 kata pertama yang valid untuk mencegah Regex Error
    teks_bersih = re.sub(r'[^\w\s]', '', teks_pasien).lower()
    kata_kunci = teks_bersih.split()
    
    if not kata_kunci:
        return "Tidak ada referensi database."

    # Cari kecocokan kata kunci sederhana
    pola_pencarian = '|'.join(kata_kunci[:3])
    matches = df_dataset[df_dataset['Context'].str.lower().str.contains(pola_pencarian, na=False)]
    
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
        # Ambil data jawaban psikolog asli dari dataset lokal menggunakan Pandas
        referensi_medis = cari_referensi_dataset(curhatan_pasien)
        
        contents_payload = []
        for msg in history:
            role = "user" if msg["sender"] == "user" else "model"
            contents_payload.append(
                types.Content(role=role, parts=[types.Part.from_text(text=msg["text"])])
            )
        
        # Gabungkan pesan terbaru dengan konteks referensi lokal di ujung payload
        prompt_dengan_konteks = (
            f"REFERENSI KASUS NYATA (Data Lokal):\n{referensi_medis}\n\n"
            f"CURHATAN PASIEN SEKARANG:\n{curhatan_pasien}"
        )
        
        contents_payload.append(
            types.Content(role="user", parts=[types.Part.from_text(text=prompt_dengan_konteks)])
        )
        
        # Kirim ke Gemini
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