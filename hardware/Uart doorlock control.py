# -*- coding: utf-8 -*-
"""
UART 시리얼 통신 기반 도어락 제어 예제 (스마트도어 키오스크)
- 제조사 제공 프로토콜 문서 기반 커스텀 바이너리 프로토콜
- 패킷 구조: STX + length + command + data + checksum + ETX
- 덧셈 체크섬으로 통신 무결성 검증
- threading.Lock 으로 시리얼 포트 동시 접근 방지

[RS485 보관함 프로토콜과의 차이]
- 보관함 RS485: 고정 7바이트, CRC16 체크섬, 비트맵으로 다수 락커 제어
- 도어락 UART : 가변 길이, 덧셈 체크섬, STX/ETX로 패킷 경계 구분
"""

import serial
import threading

PORT = '/dev/ttyUSB0'
BAUDRATE = 19200

# 패킷 고정값
DUMMY = 0xFF   # 패킷 시작 구분자
STX   = 0x04   # Start of Text
ETX   = 0x03   # End of Text

# 커맨드
CMD_STATUS   = 0x02  # 상태 조회
CMD_OPEN     = 0x03  # 문 열기
CMD_CLOSE    = 0x04  # 문 닫기

lock = threading.Lock()
client = None


# ── 시리얼 포트 ──────────────────────────────────────────

def connect(port=PORT, timeout=5):
    global client
    client = serial.Serial()
    client.port = port
    client.baudrate = BAUDRATE
    client.bytesize = 8
    client.parity = serial.PARITY_NONE
    client.stopbits = serial.STOPBITS_ONE
    client.timeout = timeout
    client.open()

def close():
    global client
    if client:
        client.close()
    client = None


# ── 패킷 생성 ────────────────────────────────────────────

def calc_checksum(length: int, command: int, data: list) -> int:
    """
    덧셈 체크섬: length + command + data 합산 후 하위 1바이트
    보관함 CRC16과 달리 단순 합산 방식
    """
    cs = length + command
    for d in data:
        cs += d
    return 0xFF & cs

def make_packet(command: int, data: list) -> bytearray:
    """
    패킷 구조:
    [0xFF, STX, length, command, data..., checksum, 0x03]
    length = command(1) + data 길이
    """
    length = 0xFF & (len(data) + 1)
    checksum = calc_checksum(length, command, data)
    return bytearray(
        [DUMMY, STX, length, command] + data + [checksum, ETX]
    )


# ── 송수신 ───────────────────────────────────────────────

def send(packet: bytearray):
    """
    패킷 전송 후 응답 수신
    응답 구조: 0xFF + STX + length + commdata + checksum + ETX
    """
    global client
    client.write(packet)

    dummy = client.read(1)
    if len(dummy) == 0 or dummy[0] != 0xFF:
        return None

    stx      = client.read(1)
    length   = client.read(1)
    commdata = client.read(length[0])
    checksum = client.read(1)
    etx      = client.read(1)

    return dummy + stx + length + commdata + checksum + etx


# ── 응답 파싱 ────────────────────────────────────────────

def parse_response(recv) -> bool:
    """
    응답 패킷 파싱
    recv[3] = 커맨드
    recv[4] = 잠금 상태 (0x00: 잠김, 0x01: 해제)
    recv[8] = 명령 결과 (0x00: 실패, 0x01: 성공)
    """
    if recv is None or len(recv) != 14:
        return False

    command = recv[3]

    if command == CMD_STATUS:
        is_open = recv[4] == 0x01
        print(f'[parse_response] 상태: {"열림" if is_open else "닫힘"}')
        return is_open

    if command == CMD_OPEN:
        success = recv[8] == 0x01 or recv[4] == 0x01 or recv[5] == 0x01
        print(f'[parse_response] 열기: {"성공" if success else "실패"}')
        return success

    if command == CMD_CLOSE:
        success = recv[8] == 0x01
        print(f'[parse_response] 닫기: {"성공" if success else "실패"}')
        return success

    return False


# ── 도어락 제어 (Lock으로 시리얼 포트 보호) ─────────────

def open_door(open_time: int = 0) -> bool:
    """
    문 열기
    open_time: 열림 유지 시간 (초), 0이면 즉시
    """
    with lock:
        try:
            connect()
            packet = make_packet(CMD_OPEN, [open_time, 0x00, 0x00, 0x00])
            recv = send(packet)
            return parse_response(recv)
        except Exception as e:
            print(f'[open_door] {e}')
            return False
        finally:
            close()

def close_door() -> bool:
    """문 닫기"""
    with lock:
        try:
            connect()
            packet = make_packet(CMD_CLOSE, [0x00, 0x00, 0x00, 0x00])
            recv = send(packet)
            return parse_response(recv)
        except Exception as e:
            print(f'[close_door] {e}')
            return False
        finally:
            close()

def get_status() -> bool:
    """문 상태 조회. True: 열림, False: 닫힘"""
    with lock:
        try:
            connect()
            packet = make_packet(CMD_STATUS, [0x00, 0x00, 0x00, 0x00])
            recv = send(packet)
            return parse_response(recv)
        except Exception as e:
            print(f'[get_status] {e}')
            return False
        finally:
            close()


# ── 실행 예제 ────────────────────────────────────────────

if __name__ == '__main__':
    print('현재 상태:', '열림' if get_status() else '닫힘')
    print('문 열기:', '성공' if open_door() else '실패')
  
