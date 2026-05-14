#!/usr/bin/env python3
# /home/hizib/python/soundkey.py
# usage: python3 soundkey.py "passwd"
# output: base64 encoded WAV (single line to stdout)
#
# 브라우저 호환성을 위해 float32 대신 int16 포맷 사용
# float32는 일부 모바일 브라우저에서 재생 불가
import sys
import base64
import io
import numpy as np
from scipy.io import wavfile

FS = 24000        # 샘플레이트 (마이크 지원 범위)
DURATION = 0.2    # 문자당 재생 시간(초)
BASE_FREQ = 8000  # 시작 주파수 (Hz)
STEP = 30         # 문자간 주파수 간격 (Hz)

def generate(data_str):
    audio_signal = []
    for char in data_str:
        freq = BASE_FREQ + (ord(char) * STEP)
        t = np.linspace(0, DURATION, int(FS * DURATION), endpoint=False)
        audio_signal.extend(0.5 * np.sin(2 * np.pi * freq * t))

    wav_data = np.array(audio_signal)
    wav_data = np.clip(wav_data, -1.0, 1.0)
    wav_data = (wav_data * 32767).astype(np.int16)

    buf = io.BytesIO()
    wavfile.write(buf, FS, wav_data)
    return buf.getvalue()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)

    data_str = sys.argv[1]  # "passwd" (6자리)
    wav_bytes = generate(data_str)
    sys.stdout.write(base64.b64encode(wav_bytes).decode())
    sys.stdout.flush()
