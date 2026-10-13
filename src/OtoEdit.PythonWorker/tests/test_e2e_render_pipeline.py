import os
import subprocess
import json
import numpy as np
import sys
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    print("=== STARTING END-TO-END RENDER PIPELINE TEST ===")

    # 1. Create a 4-second input test video with audio
    test_video = "/tmp/e2e_input.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=4:size=1280x720:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=4",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        test_video
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print("Generated test input video:", test_video)

    # 2. Create a test sticker image with alpha
    test_image = "/tmp/e2e_avatar.png"
    arr = np.zeros((200, 200, 4), dtype=np.uint8)
    arr[30:170, 30:170] = [255, 60, 100, 255]
    Image.fromarray(arr).save(test_image)

    # 3. Create dummy BGM file
    test_bgm = "/tmp/e2e_bgm.wav"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=880:duration=10", test_bgm], check=True, capture_output=True)

    # 4. Import VideoRenderer
    from render.video_renderer import VideoRenderer

    vr = VideoRenderer()
    output_file = "/tmp/e2e_final_output.mp4"

    # Create concat segments
    concat_txt = "/tmp/e2e_concat.txt"
    with open(concat_txt, "w") as f:
        f.write(f"file '{test_video}'\ninpoint 0.0\noutpoint 3.5\n")

    edl_dict = {
        "overlays": [
            {
                "id": "badge_1",
                "type": "text",
                "content": "CAPCUT STİLİ ROZET!",
                "boxStyle": "pill",
                "boxBgColor": "#4F46E5",
                "color": "#FFFFFF",
                "fontSize": 36,
                "strokeColor": "#000000",
                "strokeWidth": 2,
                "shadowColor": "#000000",
                "shadowBlur": 4,
                "allCaps": True,
                "timestamp": 0.5,
                "duration": 2.5,
                "position": ["center", "top"]
            },
            {
                "id": "img_1",
                "type": "image",
                "source": test_image,
                "stickerBorder": True,
                "stickerBorderWidth": 6,
                "stickerBorderColor": "#FFFFFF",
                "rotation": 10.0,
                "timestamp": 0.5,
                "duration": 2.5,
                "scale": 0.25,
                "position": ["center", "center"]
            }
        ],
        "settings": {
            "subtitlesEnabled": False,
            "backgroundMusic": {
                "url": test_bgm,
                "volume": 0.20,
                "autoDucking": True,
                "duckingAmount": 0.15
            }
        }
    }

    print("Calling VideoRenderer.render()...")
    result = vr.render(
        edl_json=edl_dict,
        video_path=test_video,
        output_path=output_file,
        temp_dir="/tmp"
    )

    print(f"Render completed! Output: {result}")
    assert os.path.isfile(result), "Output file does not exist!"
    size_mb = os.path.getsize(result) / (1024 * 1024)
    print(f"Output size: {size_mb:.2f} MB")

    # Probe output video streams
    probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name", "-of", "json", result]
    p_res = subprocess.run(probe_cmd, capture_output=True, text=True)
    streams = json.loads(p_res.stdout).get("streams", [])
    types = [s["codec_type"] for s in streams]
    print("Streams found in rendered video:", types)
    assert "video" in types and "audio" in types, "Missing audio or video stream!"

    print("=== E2E RENDER PIPELINE TEST SUCCEEDED 100%! ===")

if __name__ == "__main__":
    main()
