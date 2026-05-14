# -*- coding: utf-8 -*-
"""
MQTT 브로커 클라이언트 - 스마트도어 시스템

역할:
    Mosquitto 브로커와의 연결 생명주기 관리
    - 연결 / 재연결 / 구독 / 발행

핵심 설계:
    - 싱글톤 패턴: 프로세스 전체에서 인스턴스 하나만 유지
    - 자동 재연결: 지수 백오프 (1초 → 최대 120초) 로 네트워크 불안정 대응
    - clean_session=False: 재연결 시 미수신 메시지 재전달 보장
    - on_message 콜백 외부 주입: 브로커 클라이언트와 메시지 처리 로직 분리

사용 예:
    broker = MqttBroker(
        host='127.0.0.1',
        port=1883,
        topic='Exam01/#',
        onmessage=my_handler,
    )
    broker.run()
"""

import random
import threading
import time
import paho.mqtt.client as mqtt_client


# ── 설정 ─────────────────────────────────────────────────

BROKER_HOST = "127.0.0.1"
BROKER_PORT = 1883
BROKER_USER = ""
BROKER_PASS = ""


# ── 브로커 클라이언트 (싱글톤) ────────────────────────────

class MqttBroker:
    """
    싱글톤 MQTT 브로커 연결 클라이언트
    연결 생명주기(연결/재연결/구독/발행)만 담당
    메시지 처리는 onmessage 콜백으로 위임
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, **kwargs):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True

        self.host     = kwargs.get('host', BROKER_HOST)
        self.port     = kwargs.get('port', BROKER_PORT)
        self.username = kwargs.get('username', BROKER_USER)
        self.passwd   = kwargs.get('passwd',   BROKER_PASS)
        self.topic    = kwargs.get('topic')
        self.onmessage = kwargs.get('onmessage')   # 외부에서 주입받는 메시지 핸들러

        self.reconnect_delay     = 1
        self.max_reconnect_delay = 120

        self.client = self._create_client()

    # ── 클라이언트 생성 ───────────────────────────────────

    def _create_client(self) -> mqtt_client.Client:
        client_id = f"broker_{random.randint(0, 9999)}"
        try:
            client = mqtt_client.Client(
                mqtt_client.CallbackAPIVersion.VERSION1,
                client_id=client_id,
                clean_session=False,    # 재연결 시 미수신 메시지 재전달
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
            print(f"[Broker] 브로커 연결 성공")
            self.reconnect_delay = 1        # 재연결 딜레이 초기화
            if self.topic:
                self.subscribe(self.topic)
        else:
            print(f"[Broker] 연결 실패 (rc={rc})")
            self._schedule_reconnect()

    def _on_disconnect(self, client, userdata, rc):
        print(f"[Broker] 연결 끊김 (rc={rc}) → 재연결 대기")
        self._schedule_reconnect()

    def _on_message(self, client, userdata, msg):
        """수신 메시지를 외부 핸들러(onmessage)로 위임"""
        if callable(self.onmessage):
            self.onmessage(client, userdata, msg)
        else:
            print(f"[Broker] 메시지 수신 (핸들러 없음): {msg.payload.decode()}")

    # ── 재연결 ────────────────────────────────────────────

    def _schedule_reconnect(self):
        """지수 백오프 재연결 스케줄링"""
        print(f"[Broker] {self.reconnect_delay}초 후 재연결 시도")
        threading.Timer(self.reconnect_delay, self._connect).start()
        self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)

    def _connect(self):
        if self.username and self.passwd:
            self.client.username_pw_set(self.username, self.passwd)
        try:
            self.client.connect(host=self.host, port=self.port, keepalive=60)
        except Exception as e:
            print(f"[Broker] 연결 실패: {e}")
            self._schedule_reconnect()

    # ── 구독 / 발행 ───────────────────────────────────────

    def subscribe(self, topic: str):
        try:
            self.client.subscribe(topic)
            print(f"[Broker] 구독 시작: {topic}")
        except Exception as e:
            print(f"[Broker] 구독 실패: {e}")

    def publish(self, topic: str, msg: str):
        try:
            self.client.publish(topic, msg)
            print(f"[Broker] 발행: {topic} → {msg}")
        except Exception as e:
            print(f"[Broker] 발행 실패: {e}")

    # ── 실행 ─────────────────────────────────────────────

    def run(self):
        """메인 루프 실행 (블로킹)"""
        self._connect()
        self.client.loop_forever()
