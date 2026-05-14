#### 열기 명령 전체 흐름

```less
1. ctrl.py      python ctrl.py open 1 3 입력
2. LockerService  lock.acquire() → rs485.init('/dev/hunes') 포트 열기
3. rs485.py     패킷 생성 [1, 1, 1, 0, 0] → CRC16 계산 → 7바이트 전송
4. 컨트롤러 보드  응답 7바이트 반환
5. rs485.py     응답 수신 → CRC 검증 → 락커 상태 비트 확인
6. rs485.py     열기 신호 전송 → 폴링 → 초기화
7. LockerService  rs485.close() → lock.release()
```

#### 1. ctrl.py
```less
python ctrl.py open 1 3
→ jumper=1, serial=3 파싱
→ LockerService.openDoor(1, 3, '/dev/hunes') 호출
```

#### 2. LockerService.py
```less
lock.acquire()          # 다른 스레드 대기
rs485.init('/dev/hunes') # 포트 열기
rs485.openDoor(1, 3)    # 제어 위임
rs485.close()           # 포트 닫기
lock.release()          # 다음 스레드 허용
```

#### 3. rs485.py — 패킷 흐름
```less
① 상태 조회
   send(1, 1, 1, 0, 0) + CRC16 → 컨트롤러 전송
   응답 7바이트 수신 → CRC 검증
   p[3], p[4] 비트맵에서 3번 비트 확인 → 닫힘이면 진행

② 열기 신호
   serial=3 → gateToBytes → (0b00000100, 0)
   send(1, 1, 2, 0b00000100, 0) + CRC16 → 솔레노이드에 전기

③ 폴링 (0.2초 간격, 최대 5초)
   send(1, 1, 1, 0, 0) → 상태 재조회
   열렸으면 → 다음 단계
   안 열렸으면 → 반복
   5초 초과 → 강제 초기화 후 실패

④ 초기화
   send(1, 1, 2, 0, 0) → 전기 차단
   솔레노이드 과열 방지
```

#### 4. crc16.py
```less
매 send() 마다 호출
[1, 1, 1, 0, 0] → CRC16 계산 (INITIAL_MODBUS=0xFFFF)
패킷 뒤에 [CRC 하위바이트, CRC 상위바이트] 붙여서 전송
수신할 때도 똑같이 계산해서 불일치면 None 반환
```





































































