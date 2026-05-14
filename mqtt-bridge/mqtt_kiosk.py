# -*- coding: utf-8 -*-
"""
MQTT 키오스크 구독(Subscribe) 예제 - 스마트도어 시스템

구조:
    Mosquitto 브로커
        ↓ MQTT Subscribe  (hizib01/#)
    라즈베리파이 키오스크 (Python)
        ↓ request 필드 기반 라우팅
    핸들러 (도어 제어 / 사용자 / 공지 / 일정 / 메시지)

핵심 설계:
    - 싱글톤 패턴: 프로세스 전체에서 MQTT 클라이언트 인스턴스 하나만 유지
    - 자동 재연결: 지수 백오프 (1초 → 최대 120초) 로 네트워크 불안정 대응
    - 라우팅 테이블: request 필드 → 핸들러 함수 매핑으로 확장성 확보
    - 와일드카드 구독: hizib01/# 으로 모든 하위 토픽 수신
    - 메시지 구조: { "request": "/Smartdoor/...", "data": { ... } }
"""

import json
import random
import threading
import time
import urllib.parse
import paho.mqtt.client as mqtt_client


# ── 설정 ─────────────────────────────────────────────────

BROKER_HOST = "127.0.0.1"
BROKER_PORT = 1883
BROKER_USER = ""
BROKER_PASS = ""
SUBSCRIBE_TOPIC = "hizib01/#"          # 와일드카드로 모든 하위 토픽 구독


# ── 핸들러 함수 ───────────────────────────────────────────

def door_open_at_app_process(payload: dict):
    """앱 요청 도어 열기 - GPIO/시리얼로 솔레노이드 락 제어"""
    user_id = payload.get('user_id')
    print(f"[도어] 열기 요청 - user_id: {user_id}")
    # open_locker(jumper=1, serial_num=1)  # RS485 제어 연동

def door_close_at_app_process(payload: dict):
    """앱 요청 도어 닫기"""
    user_id = payload.get('user_id')
    print(f"[도어] 닫기 요청 - user_id: {user_id}")

def door_open_by_admin_process(payload: dict):
    """관리자 도어 열기"""
    print(f"[관리자] 도어 열기 - payload: {payload}")

def face_update_process(payload: dict):
    """얼굴 인식 모델 업데이트 - 사용자 등록/수정 시 트리거"""
    user_id = payload.get('user_id')
    print(f"[얼굴] 업데이트 요청 - user_id: {user_id}")
    # face_recognition.update(user_id)

def face_delete_process(payload: dict):
    """얼굴 인식 모델에서 사용자 삭제"""
    user_id = payload.get('user_id')
    print(f"[얼굴] 삭제 요청 - user_id: {user_id}")

def notice_join_process(payload: dict):
    """공지사항 등록 - 키오스크 화면 즉시 갱신"""
    print(f"[공지] 등록 - data: {payload.get('data')}")

def notice_update_process(payload: dict):
    """공지사항 수정"""
    print(f"[공지] 수정 - data: {payload.get('data')}")

def notice_delete_process(payload: dict):
    """공지사항 삭제"""
    print(f"[공지] 삭제 - data: {payload.get('data')}")

def schedule_join_process(payload: dict):
    """일정 등록"""
    print(f"[일정] 등록 - data: {payload.get('data')}")

def message_join_process(payload: dict):
    """메시지 등록"""
    print(f"[메시지] 등록 - data: {payload.get('data')}")

def admin_init_process(payload: dict):
    """키오스크 초기화 - 설정/데이터 전체 리로드"""
    print(f"[관리자] 초기화 요청")

def admin_refresh(payload: dict):
    """키오스크 화면 새로고침"""
    print(f"[관리자] 화면 새로고침")


# ── 라우팅 테이블 ─────────────────────────────────────────
# request 필드 값 → 핸들러 함수 매핑
# 핸들러 추가 시 이 테이블에만 등록하면 됨

REQUEST_HANDLERS = {
    # 도어 제어
    "/Smartdoor/doorOpenAtAppProcess":   door_open_at_app_process,
    "/Smartdoor/doorCloseAtAppProcess":  door_close_at_app_process,
    "/Smartdoor/doorOpenByAdminProcess": door_open_by_admin_process,

    # 사용자 얼굴 인식
    "/User/faceUpdateProcess":           face_update_process,
    "/User/faceDeleteProcess":           face_delete_process,

    # 공지사항
    "/SmartdoorNotice/joinProcess":      notice_join_process,
    "/SmartdoorNotice/updateProcess":    notice_update_process,
    "/SmartdoorNotice/deleteProcess":    notice_delete_process,

    # 일정
    "/SmartdoorSchedule/joinProcess":    schedule_join_process,

    # 메시지
    "/SmartdoorMessage/joinProcess":     message_join_process,

    # 관리자
    "/Admin/initProcess":                admin_init_process,
    "/Admin/refresh":                    admin_refresh,
}


# ── MQTT 클라이언트 (싱글톤) ──────────────────────────────

class MqttKiosk:
    """
    싱글톤 MQTT 구독 클라이언트
    - 프로세스 내 단일 인스턴스 보장
    - 연결 끊김 시 지수 백오프로 자동 재연결 (1초 → 최대 120초)
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True

        self.reconnect_delay = 1
        self.max_reconnect_delay = 120
        self.client = self._create_client()

    def _create_client(self) -> mqtt_client.Client:
        client_id = f"kiosk_{random.randint(0, 9999)}"
        try:
            client = mqtt_client.Client(
                mqtt_client.CallbackAPIVersion.VERSION1,
                client_id=client_id,
                clean_session=False,    # 연결 복구 시 미수신 메시지 재전달
            )
        except Exception:
            client = mqtt_client.Client(client_id=client_id, clean_session=False)

        client.on_connect    = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message    = self._on_message
        client.reconnect_delay_set(min_delay=1, max_delay=120)
        return client

    # ── 콜백 ─────────────────────────────────────────────

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"[MQTT] 브로커 연결 성공")
            self.reconnect_delay = 1            # 재연결 딜레이 초기화
            client.subscribe(SUBSCRIBE_TOPIC)   # 와일드카드 구독
            print(f"[MQTT] 구독 시작: {SUBSCRIBE_TOPIC}")
        else:
            print(f"[MQTT] 연결 실패 (rc={rc})")
            self._schedule_reconnect()

    def _on_disconnect(self, client, userdata, rc):
        print(f"[MQTT] 연결 끊김 (rc={rc}) → 재연결 대기")
        self._schedule_reconnect()

    def _on_message(self, client, userdata, msg):
        """
        메시지 수신 → request 필드로 핸들러 라우팅
        메시지 형식: { "request": "/Smartdoor/...", "data": { ... } }
        """
        try:
            raw = urllib.parse.unquote(msg.payload.decode('utf-8'))
            payload = json.loads(raw)
            request = payload.get('request')

            print(f"[MQTT] 수신 topic={msg.topic} request={request}")

            if request in REQUEST_HANDLERS:
                REQUEST_HANDLERS[request](payload)
            else:
                print(f"[MQTT] 알 수 없는 request: {request}")

        except Exception as e:
            print(f"[MQTT] 메시지 처리 오류: {e}")

    # ── 재연결 ────────────────────────────────────────────

    def _schedule_reconnect(self):
        """지수 백오프 재연결 스케줄링"""
        print(f"[MQTT] {self.reconnect_delay}초 후 재연결 시도")
        threading.Timer(self.reconnect_delay, self._connect).start()
        self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)

    def _connect(self):
        if BROKER_USER and BROKER_PASS:
            self.client.username_pw_set(BROKER_USER, BROKER_PASS)
        try:
            self.client.connect(host=BROKER_HOST, port=BROKER_PORT, keepalive=60)
        except Exception as e:
            print(f"[MQTT] 연결 실패: {e}")
            self._schedule_reconnect()

    # ── 실행 ─────────────────────────────────────────────

    def run(self):
        """메인 루프 실행 (블로킹)"""
        self._connect()
        self.client.loop_forever()


# ── 실행 예제 ─────────────────────────────────────────────

if __name__ == '__main__':
    kiosk = MqttKiosk()
    kiosk.run()
