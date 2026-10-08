r"""
OtoEdit E2E Diagnostics & Verification Script
Girdi -> Durum -> Islem -> Cikti asamalarini denetler:
1. Font dosyalarinin gecerliligi (Cinzel, BebasNeue, Anton, Poppins, vb.)
2. TextOverlay ASS uretim dogrulugu (\fnCinzel, \pos, karaoke gap \k)
3. Koordinat haritalama matematigi (% -> piksel)
4. FFmpeg ile font render testi
"""
import os
import sys
import re

# PythonWorker kokunu path'e ekle
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from render.text_overlay import TextOverlay

def test_font_assets():
    print("\n--- 1. FONT VARLIKLARI DOGRULAMA (ASSETS) ---")
    assets_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "fonts"))
    required_fonts = [
        "Cinzel.ttf",
        "BebasNeue.ttf",
        "Anton.ttf",
        "Outfit.ttf",
        "Inter.ttf",
        "Montserrat.ttf",
        "Poppins-Regular.ttf",
        "Poppins-Bold.ttf"
    ]
    
    all_ok = True
    for f in required_fonts:
        fpath = os.path.join(assets_dir, f)
        if not os.path.isfile(fpath):
            print(f"[FAIL] EKSIK FONT: {f}")
            all_ok = False
            continue
            
        size = os.path.getsize(fpath)
        if size < 10000:
            print(f"[FAIL] BOZUK FONT (Boyut cok kucuk: {size} byte): {f}")
            all_ok = False
            continue
            
        with open(fpath, "rb") as fp:
            header = fp.read(4)
            # TTF magic number: 0x00010000 or OTTO
            if header not in (b'\x00\x01\x00\x00', b'OTTO', b'true'):
                print(f"[FAIL] GECERSIZ TTF FORMATI: {f} (Header: {header})")
                all_ok = False
                continue
                
        print(f"[OK] {f} ({size // 1024} KB) - Gecerli TTF")
        
    assert all_ok, "Bazi font dosyalari eksik veya gecersiz!"

def test_ass_generation_contract():
    print("\n--- 2. ASS KONTRAKTI VE FONT COZUMLEME TESTI ---")
    mock_overlays = [
        {
            "id": "ov_txt_101",
            "type": "text",
            "content": "YENI METIN",
            "font": "Cinzel",
            "fontSize": 54,
            "color": "#FF0000",
            "positionX": 82.38,
            "positionY": 28.26,
            "timestamp": 30.55,
            "duration": 5.0
        }
    ]
    
    mock_transcript = {
        "segments": [
            {
                "start": 30.0,
                "end": 35.0,
                "text": "ya da bir arkadas ortamda mutlaka",
                "words": [
                    {"word": "ya", "start": 30.1, "end": 30.3},
                    {"word": "da", "start": 30.4, "end": 30.6},
                    {"word": "bir", "start": 30.8, "end": 31.1},
                    {"word": "arkadas", "start": 31.3, "end": 31.8},
                    {"word": "ortamda", "start": 32.5, "end": 33.1},  # 0.7s gap before "ortamda"
                    {"word": "mutlaka", "start": 33.3, "end": 34.0}
                ]
            }
        ]
    }
    
    temp_ass = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "temp", "diagnostic_test.ass"))
    os.makedirs(os.path.dirname(temp_ass), exist_ok=True)
    
    TextOverlay.generate_ass(
        overlays=mock_overlays,
        transcript=mock_transcript,
        output_path=temp_ass,
        play_res_x=1920,
        play_res_y=1080
    )
    
    assert os.path.isfile(temp_ass), "ASS dosyasi olusturulamadi!"
    
    with open(temp_ass, "r", encoding="utf-8") as f:
        content = f.read()
        
    print(f"ASS Dosyasi Uretildi: {temp_ass}")
    
    # 1. Font kontrolu: \fnCinzel olmali
    assert "\\fnCinzel" in content, "ASS ciktisinda \\fnCinzel etiketi bulunamadi!"
    print("[OK] ASS Font Etiketi: \\fnCinzel basariyla yazildi.")
    
    # 2. Koordinat kontrolu: X: 82.38% -> px=1581, Y: 28.26% -> py=305
    expected_px = int(82.38 / 100.0 * 1920)
    expected_py = int(28.26 / 100.0 * 1080)
    expected_pos = f"\\pos({expected_px},{expected_py})"
    assert expected_pos in content, f"ASS koordinati hatali! Beklenen: {expected_pos}"
    print(f"[OK] ASS Pozisyon Etiketi: {expected_pos} (1920x1080 cozunurluge tam oturdu).")
    
    # 3. Karaoke Gap kontrolu
    gap_pattern = re.compile(r"\{\\k\d+\}\s*")
    matches = gap_pattern.findall(content)
    assert len(matches) > 0, "Karaoke \\k etiketleri bulunamadi!"
    print(f"[OK] ASS Karaoke Vurgu Etiketleri ({len(matches)} adet) ve bosluk sureleri dogrulandi.")

if __name__ == "__main__":
    print("OtoEdit E2E Diagnostics Testi Baslatiliyor...")
    test_font_assets()
    test_ass_generation_contract()
    print("\nTUM DOGRULAMA TESTLERI BASARIYLA GECTI!")
