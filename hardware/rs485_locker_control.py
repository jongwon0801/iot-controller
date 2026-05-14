# -*- coding: utf-8 -*-
"""
RS485 통신 기반 솔레노이드 락커 제어 예제
- RS485 커스텀 바이너리 프로토콜, CRC16으로 통신 무결성 검증
- 문 열기: 상태 확인 → 신호 전송 → 폴링 → 초기화
- threading.Lock 으로 RS485 단일 버스 동시 접근 방지
"""

import serial
import threading
import time
from crc16 import calcString, INITIAL_MODBUS  # Modbus CRC16

PORT = '/dev/ttyUSB0'
BAUDRATE = 9600
OPEN_TIMEOUT = 5.0   # 문 열림 대기 최대 시간 (초)
POLL_INTERVAL = 0.2  # 상태 폴링 간격 (초)

ser = serial.Serial()
lock = threading.Lock()


# ── 시리얼 포트 ──────────────────────────────────────────

def init(port=PORT):
    global ser
    ser.port = port
    ser.baudrate = BAUDRATE
    ser.bytesize = 8
    ser.parity = serial.PARITY_NONE
    ser.stopbits = serial.STOPBITS_ONE
    ser.timeout = 1
    try:
        ser.open()
    except Exception:
        ser.close()
        ser.open()
    ser.flushInput()
    ser.flushOutput()

def close():
    global ser
    ser.close()


# ── 패킷 생성 / 송수신 ───────────────────────────────────

def make_crc(data: tuple) -> int:
    """Modbus RTU CRC16 계산"""
    s = ''.join(chr(b) for b in data)
    return calcString(s, INITIAL_MODBUS)

def send_packet(data: tuple):
    """데이터 튜플에 CRC16 붙여서 전송 (총 7바이트)"""
    crc = make_crc(data)
    sd = bytearray(data)
    sd.append(crc & 0xFF)
    sd.append(crc >> 8 & 0xFF)
    ser.write(sd)
    ser.flushOutput()

def read_packet():
    """7바이트 응답 수신 후 CRC 검증, 실패 시 None 반환"""
    try:
        p = ser.read(7)
        if len(p) != 7:
            return None
        data = tuple(p[:5])
        crc = make_crc(data)
        if p[5] == (crc & 0xFF) and p[6] == (crc >> 8 & 0xFF):
            return data
    except Exception as e:
        print(f'[read_packet] {e}')
    return None

def send(data: tuple):
    send_packet(data)
    return read_packet()


# ── 솔레노이드 주소 변환 ─────────────────────────────────

def serial_to_gate(serial_num: int) -> tuple:
    """
    락커 번호 → 비트 마스크 변환
    1~8번:  하위 바이트 비트 사용
    9~16번: 상위 바이트 비트 사용
    예) serial=1 → (0b00000001, 0)
        serial=9 → (0, 0b00000001)
    """
    import math
    if serial_num < 9:
        return (int(math.pow(2, serial_num - 1)), 0)
    else:
        return (0, int(math.pow(2, serial_num - 9)))

def is_closed(status: tuple, serial_num: int) -> bool:
    """상태 패킷에서 해당 락커가 닫혀있는지 확인"""
    import math
    if serial_num < 9:
        return status[3] & int(math.pow(2, serial_num - 1)) == 0
    else:
        return status[4] & int(math.pow(2, serial_num - 9)) == 0


# ── 락커 제어 (Lock으로 RS485 단일 버스 보호) ────────────

def open_locker(jumper: int, serial_num: int, port=PORT) -> bool:
    """
    락커 열기
    1. 상태 조회로 닫힘 확인
    2. 솔레노이드에 전기 신호 전송
    3. 열림 상태 폴링 (최대 OPEN_TIMEOUT 초)
    4. 열리면 초기화 명령으로 전기 차단
    5. 타임아웃 시 강제 초기화 후 False 반환
    """
    with lock:
        try:
            init(port)

            # 1. 상태 확인
            status = send((jumper, 1, 1, 0, 0))
            if status is None:
                print('[open_locker] 상태 조회 실패')
                return False
            if not is_closed(status, serial_num):
                print('[open_locker] 이미 열려있음')
                return False

            # 2. 전기 신호 전송
            gate = serial_to_gate(serial_num)
            result = send((jumper, 1, 2, gate[0], gate[1]))
            if result is None:
                send((jumper, 1, 2, 0, 0))  # 강제 초기화
                print('[open_locker] 신호 전송 실패')
                return False

            # 3. 열림 상태 폴링
            elapsed = 0.0
            while elapsed < OPEN_TIMEOUT:
                status = send((jumper, 1, 1, 0, 0))
                if status and not is_closed(status, serial_num):
                    # 4. 열렸으면 전기 차단
                    send((jumper, 1, 2, 0, 0))
                    return True
                time.sleep(POLL_INTERVAL)
                elapsed += POLL_INTERVAL

            # 5. 타임아웃 → 강제 초기화
            send((jumper, 1, 2, 0, 0))
            print('[open_locker] 타임아웃: 강제 초기화')
            return False

        except Exception as e:
            print(f'[open_locker] {e}')
            return False
        finally:
            close()          # 예외 발생해도 반드시 포트 닫기
            # lock 은 with 블록이 자동 해제


def get_status(jumper: int, port=PORT):
    """락커 전체 상태 조회"""
    with lock:
        try:
            init(port)
            return send((jumper, 1, 1, 0, 0))
        finally:
            close()


# ── 실행 예제 ────────────────────────────────────────────

if __name__ == '__main__':
    # jumper=1 컨트롤러의 3번 락커 열기
    success = open_locker(jumper=1, serial_num=3)
    print('열기 성공' if success else '열기 실패')
