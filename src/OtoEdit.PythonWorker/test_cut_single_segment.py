import os
import tempfile
from render.video_renderer import VideoRenderer
from unittest.mock import patch, MagicMock

def test_cut():
    renderer = VideoRenderer(minio_client=MagicMock())
    with tempfile.TemporaryDirectory() as temp_dir:
        # mock subprocess.run to avoid running actual ffmpeg
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = 'mock success'
            # mock os.path.isfile and getsize to simulate ffmpeg created the file
            with patch('os.path.isfile', return_value=True), patch('os.path.getsize', return_value=2000):
                # We need to test the inner function _cut_single_segment.
                # Since it's nested in _execute_ffmpeg_with_concat, we can't easily call it.
                # Let's mock _parse_concat_file and threadpool to run it, or we can just mock subprocess.run 
                # inside _execute_ffmpeg_with_concat and pass a dummy concat file.
                
                concat_path = os.path.join(temp_dir, 'cuts_dummy.txt')
                with open(concat_path, 'w') as f:
                    f.write('ffconcat version 1.0\n')
                    f.write('file /tmp/dummy.mp4\n')
                    f.write('inpoint 10.0\n')
                    f.write('outpoint 12.0\n')

                renderer._execute_ffmpeg_with_concat(
                    concat_txt_path=concat_path,
                    target_format='16:9',
                    face_data=None,
                    ass_path=None,
                    output_path=os.path.join(temp_dir, 'out.mp4')
                )
                
                # Check how subprocess.run was called for the segment cut
                # First call should be the NVENC attempt
                calls = mock_run.call_args_list
                if len(calls) > 0:
                    first_call_args = calls[0][0][0] # The command list
                    # Verify that '-ss' comes BEFORE '-i'
                    ss_idx = first_call_args.index('-ss')
                    i_idx = first_call_args.index('-i')
                    assert ss_idx < i_idx, f'-ss must be before -i, got {first_call_args}'
                    print('✅ TEST PASSED: -ss is before -i (Input Seeking is working!)')
                else:
                    print('❌ TEST FAILED: subprocess.run was not called')

if __name__ == '__main__':
    test_cut()
