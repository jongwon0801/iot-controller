import os
import json
import sounddevice as sd
import soundfile as sf
from openai import OpenAI

class VoiceControlManager:
    """
    OpenAI Whisper & GPT-4o-mini를 이용한 스마트 도어 제어 모듈
    """
    def __init__(self, api_key=None):
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.sample_rate = 24000
        self.record_folder = "./sounds"

    def _find_mic_device(self, target_name="USB 4K Live Camera"):
        """시스템 내 특정 오디오 입력 장치(마이크) 탐색"""
        devices = sd.query_devices()
        for idx, device in enumerate(devices):
            if device["max_input_channels"] > 0 and target_name in device["name"]:
                return idx
        return None

    def record_audio(self, duration=2, filename="voice_input.wav"):
        """음성 데이터 녹음 및 파일 저장"""
        mic_idx = self._find_mic_device()
        if mic_idx is None: return None

        os.makedirs(self.record_folder, exist_ok=True)
        filepath = os.path.join(self.record_folder, filename)

        # 녹음 실행
        recording = sd.rec(int(duration * self.sample_rate), 
                           samplerate=self.sample_rate, channels=1)
        sd.wait()
        sf.write(filepath, recording, self.sample_rate)
        return filepath

    def speech_to_text(self, audio_path):
        """Whisper API를 이용한 음성 텍스트 변환(STT)"""
        with open(audio_path, "rb") as audio_file:
            transcript = self.client.audio.transcriptions.create(
                model="whisper-1", file=audio_file
            )
        return transcript.text.strip()

    def analyze_intent(self, user_text):
        """GPT-4o-mini를 이용한 사용자 의도 파싱(NLU)"""
        system_prompt = (
            "Determine the user's intent for a smart door system. "
            "Options: door_open, turn_on, turn_off, unknown. Respond in JSON."
        )
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            response_format={"type": "json_object"}, # JSON 출력 강제
            temperature=0
        )
        
        result = json.loads(response.choices[0].message.content)
        return result.get("intent", "unknown")

    def process_voice_command(self):
        """전체 프로세스 실행 (녹음 -> 인식 -> 의도 파악 -> 실행)"""
        audio_file = self.record_audio()
        if not audio_file: return

        text = self.speech_to_text(audio_file)
        intent = self.analyze_intent(text)

        # 인텐트에 따른 함수 매핑 (예시)
        actions = {
            "door_open": lambda: print("🚪 도어 오픈 실행"),
            "turn_on": lambda: print("💡 전등 켜기 실행"),
            "turn_off": lambda: print("🔌 전등 끄기 실행")
        }
        
        action = actions.get(intent)
        if action:
            action()
        else:
            print(f"❓ 알 수 없는 명령: {text}")

if __name__ == "__main__":
    manager = VoiceControlManager()
    manager.process_voice_command()
  
