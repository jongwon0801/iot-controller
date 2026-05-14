import sounddevice as sd
import numpy as np
import threading
import time

# --- 설정값 ---
FS = 24000
DURATION = 0.2
BASE_FREQ = 8000
STEP = 30
THRESHOLD = 0.6
TIMEOUT_SEC = 5  # 5초간 소득 없으면 자동 종료


def get_camera_mic_index():
    """카메라에 내장된 USB 마이크 인덱스 찾기"""
    devices = sd.query_devices()
    for idx, device in enumerate(devices):
        if device["max_input_channels"] > 0 and (
            "USB 4K Live Camera" in device["name"] or "Camera" in device["name"]
        ):
            return idx
    return None


class SoundkeyDecoder:
    def __init__(self, on_decoded=None, logger=None):
        self.on_decoded = on_decoded
        self.logger = logger
        self._stream = None
        self._lock = threading.Lock()  # 자원 동기화를 위한 뮤텍스
        self._is_running = False  # 중복 실행 방지용 상태 플래그

        self._buffer = ""  # 수신된 문자열 저장
        self._last_char = ""  # 직전 수신 문자 (중복 수신 방지)
        self._silence_count = 0  # 무음(노이즈 이하) 카운트
        self._silence_limit = 5  # 약 1초(0.2s * 5) 무음 시 버퍼 초기화
        self._start_time = 0  # 수신 시작 시각

    def _decode_callback(self, indata, frames, time_info, status):
        """마이크 데이터를 실시간 분석하는 콜백 함수 (오디오 스레드에서 동작)"""
        if status:
            if self.logger:
                self.logger.error(f"[soundkey] 하드웨어 상태 이상: {status}")

        # 1. 타임아웃 체크 (버튼 누른 후 5초 지나면 강제 종료)
        if time.time() - self._start_time > TIMEOUT_SEC:
            if self.logger:
                self.logger.info(f"[soundkey] {TIMEOUT_SEC}초 경과로 자동 종료")
            self.stop()
            return

        # 2. 오디오 데이터 전처리 (Hanning 윈도우 적용하여 노이즈 감소)
        window = np.hanning(len(indata))
        audio_data = indata[:, 0] * window

        # 3. FFT(고속 푸리에 변환)를 통해 주파수 분석
        fft_data = np.fft.rfft(audio_data)
        freqs = np.fft.rfftfreq(len(audio_data), 1 / FS)
        magnitude = np.abs(fft_data)

        peak_index = np.argmax(magnitude)
        peak_freq = freqs[peak_index]
        peak_mag = magnitude[peak_index]

        # 4. 주파수 해석 (특정 임계값 이상의 소리만 처리)
        if peak_mag > THRESHOLD:
            # 주파수를 문자로 변환 (주파수 -> 아스키코드)
            char_code = int(round((peak_freq - BASE_FREQ) / STEP))

            if 32 <= char_code <= 126:
                current_char = chr(char_code)

                # 동일 문자가 연속해서 들어올 경우 1번만 기록 (Debouncing)
                if current_char != self._last_char:
                    self._buffer += current_char
                    self._last_char = current_char
                    if self.logger:
                        self.logger.info(f"[soundkey] 수신 중... 버퍼: {self._buffer}")

                self._silence_count = 0  # 소리가 들리므로 무음 카운트 초기화

                # 5. 6자리 완성 시 처리
                if len(self._buffer) >= 6:
                    passwd = self._buffer[:6]
                    if self.logger:
                        self.logger.info(f"[soundkey] 인증 번호 완성: {passwd}")
                    self.stop()  # 즉시 수신 종료

                    if self.on_decoded:
                        # 메인 로직(서버 검증 등) 실행 시 별도 스레드로 분리하여 오디오 스레드 방해 금지
                        threading.Thread(
                            target=self.on_decoded, args=(passwd,), daemon=True
                        ).start()
        else:
            # 소음이 THRESHOLD 미만일 때 (문자와 문자 사이 혹은 완전 무음)
            self._last_char = ""
            self._silence_count += 1

            # 약 1초 동안 의미 있는 소리가 없으면 이전 버퍼 삭제 (찌꺼기 제거)
            if self._silence_count >= self._silence_limit:
                if self._buffer != "":
                    self._buffer = ""
                    if self.logger:
                        self.logger.info("[soundkey] 무음 지속으로 버퍼 초기화")
                self._silence_count = 0

    def start(self):
        """음파 수신 시작 (이미 실행 중이면 중복 실행 방지)"""
        if self._is_running:
            if self.logger:
                self.logger.warning("[soundkey] 이미 작동 중입니다. 요청을 무시합니다.")
            return

        with self._lock:
            mic_idx = get_camera_mic_index()
            if mic_idx is None:
                if self.logger:
                    self.logger.error("[soundkey] 마이크 장치를 찾을 수 없습니다.")
                return

            # 변수 초기화
            self._buffer = ""
            self._last_char = ""
            self._silence_count = 0
            self._start_time = time.time()
            self._is_running = True

            try:
                self._stream = sd.InputStream(
                    device=mic_idx,
                    channels=1,
                    samplerate=FS,
                    blocksize=int(FS * DURATION),
                    callback=self._decode_callback,
                )
                self._stream.start()
                if self.logger:
                    self.logger.info("[soundkey] 사운드 수신 스레드 가동 성공")
            except Exception as e:
                self._is_running = False
                if self.logger:
                    self.logger.error(f"[soundkey] 스트림 시작 오류: {e}")

    def stop(self):
        """스트림 종료 요청 (Deadlock 방지를 위해 별도 스레드에서 실행)"""
        threading.Thread(target=self.stop_internal, daemon=True).start()

    def stop_internal(self):
        """실제 하드웨어 자원을 해제하고 상태를 변경"""
        with self._lock:
            if self._stream:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"[soundkey] 자원 해제 중 에러: {e}")
                finally:
                    self._stream = None
                    self._is_running = False  # 이제 다시 start 가능
                    if self.logger:
                        self.logger.info("[soundkey] 마이크 수신 정상 종료")
