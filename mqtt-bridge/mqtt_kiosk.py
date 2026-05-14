# -*- coding: utf-8 -*-
"""
MQTT 키오스크 구독/라우팅 - 스마트도어 시스템

역할:
    브로커에서 수신한 메시지를 request 필드 기준으로 핸들러에 라우팅

구조:
    Mosquitto 브로커
        ↓ MQTT Subscribe  (Exam01/#)
    MqttBroker (mqtt_broker.py)      ← 연결 생명주기 담당
    MqttKiosk (이 파일)               ← 메시지 라우팅/처리 담당
        ↓ REQUEST_HANDLERS 테이블
    핸들러 (도어 제어 / 사용자 / 공지 / 일정 / 메시지)
"""

import json
import urllib.parse
from mqtt_broker import MqttBroker


# ── 구독 토픽 ─────────────────────────────────────────────

SUBSCRIBE_TOPIC = "Exam01/#"      


# ── 핸들러 함수 ───────────────────────────────────────────

def door_open_at_app_process(payload: dict):
    """앱 요청 도어 열기 - GPIO/시리얼로 솔레노이드 락 제어"""
    user_id = payload.get('user_id')
    print(f"[도어] 열기 요청 - user_id: {user_id}")

def door_close_at_app_process(payload: dict):
    """앱 요청 도어 닫기"""
    user_id = payload.get('user_id')
    print(f"[도어] 닫기 요청 - user_id: {user_id}")

def door_open_by_admin_process(payload: dict):
    """관리자 도어 열기"""
    print(f"[관리자] 도어 열기 - payload: {payload}")

def face_update_process(payload: dict):
    """얼굴 인식 모델 업데이트"""
    user_id = payload.get('user_id')
    print(f"[얼굴] 업데이트 요청 - user_id: {user_id}")

def face_delete_process(payload: dict):
    """얼굴 인식 모델에서 사용자 삭제"""
    user_id = payload.get('user_id')
    print(f"[얼굴] 삭제 요청 - user_id: {user_id}")

def notice_join_process(payload: dict):
    """공지사항 등록"""
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
    """키오스크 초기화"""
    print(f"[관리자] 초기화 요청")

def admin_refresh(payload: dict):
    """키오스크 화면 새로고침"""
    print(f"[관리자] 화면 새로고침")


# ── 라우팅 테이블 ─────────────────────────────────────────

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


# ── 키오스크 메시지 처리 ──────────────────────────────────

class MqttKiosk:
    """
    MQTT 메시지 라우팅/처리 담당
    """

    def on_message(self, client, userdata, msg):
        """
        메시지 수신 → request 필드로 핸들러 라우팅
        """
        try:
            # URL 인코딩 대응 및 JSON 파싱
            raw = urllib.parse.unquote(msg.payload.decode('utf-8'))
            payload = json.loads(raw)
            request = payload.get('request')

            print(f"[Kiosk] 수신 topic={msg.topic} request={request}")

            if request in REQUEST_HANDLERS:
                REQUEST_HANDLERS[request](payload)
            else:
                print(f"[Kiosk] 알 수 없는 request: {request}")

        except Exception as e:
            print(f"[Kiosk] 메시지 처리 오류: {e}")


# ── 실행 예제 ─────────────────────────────────────────────

if __name__ == '__main__':
    kiosk = MqttKiosk()

    broker = MqttBroker(
        host='127.0.0.1',
        port=1883,
        topic=SUBSCRIBE_TOPIC,          # Exam01/# 구독
        onmessage=kiosk.on_message,
    )
    broker.run()
