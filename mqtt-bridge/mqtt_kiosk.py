# -*- coding: utf-8 -*-
"""
MQTT 키오스크 구독/라우팅 - 스마트도어 시스템

역할:
    브로커에서 수신한 메시지를 request 필드 기준으로 핸들러에 라우팅

구조:
    Mosquitto 브로커
        ↓ MQTT Subscribe  (hizib01/#)
    MqttBroker (mqtt_broker.py)     ← 연결 생명주기 담당
        ↓ onmessage 콜백
    MqttKiosk (이 파일)              ← 메시지 라우팅/처리 담당
        ↓ REQUEST_HANDLERS 테이블
    핸들러 (도어 제어 / 사용자 / 공지 / 일정 / 메시지)

핵심 설계:
    - 라우팅 테이블: request 필드 → 핸들러 함수 매핑으로 확장성 확보
    - 와일드카드 구독: hizib01/# 으로 모든 하위 토픽 수신
    - 메시지 구조: { "request": "/Smartdoor/...", "data": { ... } }
    - 브로커 연결 로직은 MqttBroker에 위임, 이 클래스는 처리만 담당
"""

import json
import urllib.parse
from mqtt_broker import MqttBroker


# ── 구독 토픽 ─────────────────────────────────────────────

SUBSCRIBE_TOPIC = "hizib01/#"      # 와일드카드로 모든 하위 토픽 구독


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


# ── 키오스크 메시지 처리 ──────────────────────────────────

class MqttKiosk:
    """
    MQTT 메시지 라우팅/처리 담당
    브로커 연결은 MqttBroker에 위임
    """

    def on_message(self, client, userdata, msg):
        """
        메시지 수신 → request 필드로 핸들러 라우팅
        메시지 형식: { "request": "/Smartdoor/...", "data": { ... } }
        """
        try:
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
        topic=SUBSCRIBE_TOPIC,
        onmessage=kiosk.on_message,     # 메시지 처리를 키오스크에 위임
    )
    broker.run()
