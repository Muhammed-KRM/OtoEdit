import subprocess
import os
import sys

def extract_frame(video_path, time_sec, output_path):
    """Belirli bir zamandaki frame'i PNG olarak çıkartır."""
    subprocess.run([
        "ffmpeg", "-y",
        "-ss", str(time_sec),
        "-i", video_path,
        "-vframes", "1",
        "-q:v", "2",
        output_path
    ], capture_output=True, check=True)

def test_font_rendering_visual():
    print("\n--- Test: Font Rendering ---")
    os.makedirs("/app/temp", exist_ok=True)
    input_vid = "/app/temp/test_font_input.mp4"
    ass_file = "/app/temp/test_font.ass"
    out_vid = "/app/temp/test_font_output.mp4"
    frame_img = "/app/temp/test_font_frame.png"
    
    print("1. Siyah test videosu oluşturuluyor...")
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=1920x1080:d=2",
        "-c:v", "libx264", input_vid
    ], capture_output=True)
    
    print("2. ASS dosyası oluşturuluyor...")
    ass_content = """[Script Info]
PlayResX: 1920
PlayResY: 1080
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Inter V,72,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,3,2,2,40,40,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,FONT TEST
"""
    with open(ass_file, "w") as f:
        f.write(ass_content)
    
    print("3. FFmpeg ile font render ediliyor...")
    subprocess.run([
        "ffmpeg", "-y", "-i", input_vid,
        "-vf", f"ass='{ass_file}'",
        "-c:v", "libx264", out_vid
    ], capture_output=True)
    
    print("4. Frame çıkartılıyor...")
    extract_frame(out_vid, 1.0, frame_img)
    
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        print("Pillow veya numpy yüklü değil, görsel doğrulama atlanıyor.")
        return
        
    print("5. Pikseller kontrol ediliyor...")
    img = np.array(Image.open(frame_img))
    
    # Alt yari bolgesi (y >= 540)
    bottom_half = img[540:, :]
    white_pixels = np.sum(bottom_half > 200)
    
    if white_pixels > 100:
        print(f"✅ Font testi geçti. Beyaz piksel: {white_pixels}")
    else:
        print(f"❌ FONT RENDER EDILMEDI! Beyaz piksel sayısı: {white_pixels}")


def test_subtitle_sync_visual():
    print("\n--- Test: Subtitle Sync ---")
    input_vid = "/app/temp/test_sync_input.mp4"
    ass_file = "/app/temp/test_sync.ass"
    out_vid = "/app/temp/test_sync_output.mp4"
    
    print("1. 10 saniyelik sayaçlı test videosu oluşturuluyor...")
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", "color=c=blue:s=1920x1080:d=10:r=30",
        "-vf", "drawtext=text='%{pts\\\\:hms}':fontsize=72:fontcolor=white:x=10:y=10",
        "-c:v", "libx264", "-an",
        input_vid
    ], capture_output=True)
    
    print("2. ASS dosyası oluşturuluyor...")
    ass = """[Script Info]
PlayResX: 1920
PlayResY: 1080
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,72,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,3,2,2,40,40,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:02.00,0:00:04.00,Default,,0,0,0,,MARKER_A
Dialogue: 0,0:00:06.00,0:00:08.00,Default,,0,0,0,,MARKER_B
"""
    with open(ass_file, "w") as f:
        f.write(ass)
    
    print("3. Altyazı render ediliyor...")
    subprocess.run([
        "ffmpeg", "-y", "-i", input_vid,
        "-vf", f"ass='{ass_file}'",
        "-c:v", "libx264",
        out_vid
    ], capture_output=True)
    
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        print("Pillow veya numpy yüklü değil, atlanıyor.")
        return

    print("4. Frame'ler kontrol ediliyor...")
    for t, expected in [(1.0, False), (3.0, True), (5.0, False), (7.0, True)]:
        frame_out = f"/app/temp/frame_{int(t)}s.png"
        extract_frame(out_vid, t, frame_out)
        
        img = np.array(Image.open(frame_out))
        # Yalnızca alt yarıyı (y > 540) kontrol et, sayaç (y=10) üstte kalıyor
        bottom = img[540:, :, 0:2]
        has_subtitle = np.max(bottom) > 200
        
        status = "✅" if has_subtitle == expected else "❌"
        print(f"{status} t={t}s: Altyazı {'olmalı' if expected else 'olmamalı'} "
              f"ve {'var' if has_subtitle else 'yok'} (max pixel: {np.max(bottom)})")

if __name__ == "__main__":
    test_font_rendering_visual()
    test_subtitle_sync_visual()
