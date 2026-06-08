import os
import random
import re
import time
import pandas as pd
from flask import Flask, render_template, request, jsonify
from google import genai
from google.genai import types

app = Flask(__name__)

# 1. INISIALISASI GEMINI CLIENT
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "API")
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
    kata_kunci_bahaya = [
        # BAHASA INDONESIA
        'bunuh diri', 'bunuhdiri', 'akhiri hidup', 'mengakhiri hidup', 'cabut nyawa',
        'ingin mati', 'pengen mati', 'mau mati', 'mending mati', 'mending aku mati',
        'mati saja', 'mati aja', 'cara mati', 'biarkan aku mati', 'lebih baik mati',
        'kalau aku mati', 'dengan mati', 'dibunuh', 'tiada',
        'tidur selamanya', 'lenyap dari dunia', 'menyusul tuhan',
        'selamat tinggal dunia', 'akhir dari segalanya', 'sudah saatnya aku pergi',
        'tidak hidup', 'tetap hidup', 'nyerah sama hidup', 'capek hidup',
        'gak kuat hidup', 'nggak kuat hidup',
        'self harm', 'self-harm', 'menyakiti diri', 'menyakiti diriku', 'melukai diri',
        'nyilet', 'menyayat', 'sayat', 'cutting', 'potong nadi',
        'gantung diri', 'lompat', 'loncat', 'nabrakin diri', 'menabrakkan diri',
        'racun', 'baygon', 'overdosis', 'telan pil', 'puluhan pil',
        'menusuk', 'surat wasiat', 'pesan terakhir',
        # BAHASA INGGRIS
        'suicide', 'kill myself', 'killing myself', 'want to die', 'end my life', 'end it all',
        'rather be dead', 'rather die', 'stop living', 'dont want to live', "don't want to live",
        'sleep forever', 'better off dead', 'take my own life', 'take my life', 'ready to die',
        'just die', 'let me die', 'if i die', 'die painlessly', 'by dying',
        'cut myself', 'cutting myself', 'cutting my', 'cut my arm',
        'slit my wrists', 'hang myself', 'swallow pills', 'poison', 'bug spray',
        'jump off', 'jumping off', 'jump from', 'about to jump',
        'stab myself', 'hurt myself', 'hurting myself', 'harm myself', 'swallow a bottle',
        'dozens of pills', 'suicide note', 'done with life', 'no reason to live',
        'goodbye world', 'goodbye everyone', 'end the pain forever', 'way out of this life',
        "wasn't alive", 'stay alive', 'disappear from this world', 'throw myself',
        'bear living', "i'm gone", 'be killed'
        ]
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
    
    # Kamus Terjemahan Keyword Sederhana (Indo -> Inggris)
    kamus_keyword = {
        'tidur': 'sleep', 'depresi': 'depress', 'cemas': 'anxiety', 'panik': 'panic',
        'sedih': 'sad', 'marah': 'angry', 'takut': 'fear', 'bingung': 'confused',
        'putus': 'breakup', 'keluarga': 'family', 'teman': 'friend', 'pacar': 'boyfriend',
        'kerja': 'job', 'lelah': 'tired', 'capek': 'tired', 'stres': 'stress',
        'berguna': 'worthless', 'benci': 'hate', 'gagal': 'failure', 'nangis': 'cry',
        'trauma': 'trauma', 'insecure': 'insecure', 'overthinking': 'think', 'sendiri': 'lonely'
    }
    
    # Bersihkan tanda baca dan ambil 3 kata pertama yang valid untuk mencegah Regex Error
    teks_bersih = re.sub(r'[^\w\s]', '', teks_pasien).lower()
    kata_kunci = teks_bersih.split()
    
    if not kata_kunci:
        return "Tidak ada referensi database."

    # Mapping/Terjemahkan kata kunci
    kata_kunci_pencarian = []
    for kata in kata_kunci:
        if kata in kamus_keyword:
            kata_kunci_pencarian.append(kamus_keyword[kata])
        elif len(kata) > 3: # Masukkan kata asli jika cukup panjang
            kata_kunci_pencarian.append(kata)
            
    if not kata_kunci_pencarian:
        return df_dataset.iloc[random.randint(0, len(df_dataset)-1)]['Response']
    
    # Cari kecocokan kata kunci sederhana
    pola_pencarian = '|'.join(kata_kunci_pencarian[:4]) # Maksimal ambil 4 keyword utama
    matches = df_dataset[df_dataset['Context'].str.lower().str.contains(pola_pencarian, na=False, regex=True)]
    
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
    
    print(f"\n[ARSITEKTUR STEP 1] Menerima input user: '{curhatan_pasien}'")
    
    if not curhatan_pasien.strip():
        print("[ARSITEKTUR STEP 1.5] Pesan kosong ditolak.")
        return jsonify({"response": "Eh, pesannya kosong nih. Cerita yuk, aku dengerin."})
    
    pesan_darurat = cek_kondisi_darurat(curhatan_pasien)
    if pesan_darurat:
        print("[ARSITEKTUR STEP 2] GUARDRAIL AKTIF: Kondisi darurat dicegat!")
        return jsonify({"response": pesan_darurat})
    
    print("[ARSITEKTUR STEP 2] Guardrail Aman. Memulai proses RAG.")
    try:
        start_rag = time.time()
        # Ambil data jawaban psikolog asli dari dataset lokal menggunakan Pandas
        referensi_medis = cari_referensi_dataset(curhatan_pasien)
        end_rag = time.time()
        print(f"[ARSITEKTUR STEP 3] RAG Selesai ({end_rag - start_rag:.3f} detik). Referensi {'ditemukan' if 'Tidak ada' not in referensi_medis else 'acak diambil'}.")
        
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
        
        print("[ARSITEKTUR STEP 4] Mengirim gabungan prompt ke Gemini API...")
        start_api = time.time()
        
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
        end_api = time.time()
        print(f"[ARSITEKTUR STEP 5] Respons diterima dari Gemini ({end_api - start_api:.2f} detik). Mengirim ke UI.")
        
        return jsonify({"response": response.text})
    except Exception as e:
        return jsonify({"response": f"Aduh maaf, otak backend aku lagi nge-blank semenit: {str(e)}"})

if __name__ == '__main__':
    app.run(debug=True)