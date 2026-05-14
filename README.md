#### 🛠️ IoT Hardware Control (Python)
```less
실제 운영 제품(스마트도어, 무인보관함)의 하드웨어 제어 로직

실제 운영 환경의 기술적 한계를 분석하고, 사용자 경험(UX) 개선을 위해
다중 디스플레이 인터페이스와 실시간 미디어 통신 구조를 설계 및 구현한 기록입니다.
```

#### 🔌 Tech Stack & Hardware

| 분류                 | 상세 내용                                                                |
| ------------------ | -------------------------------------------------------------------- |
| Communication      | WebSocket, MQTT, UART(TTY), RS232/RS485 통신, GPIO 제어                  |
| Hardware           | Raspberry Pi 4 기반 스마트도어 시스템, Solenoid Door Lock, PIR/Gas/Flame 센서 연동 |
| Device Integration | USB 4K 카메라 및 오디오 디바이스 제어, RS232 장비 연동, PG 결제 단말기 연동                  |
| Backend            | Python Tornado 기반 실시간 서버 및 WebSocket 통신 개발                           |
| Frontend / GUI     | PySide6(Qt), Kivy 기반 보관함 UI 유지보수 및 기능 개선                             |
| Linux System       | Linux 디바이스 관리(udev, lsusb), Shell Script 자동화, X11 세션 제어              |
| Smart System       | 얼굴인식/QR 인증 기반 출입 제어 및 센서 연동 시스템 구현                                   |


#### 폴더 구조
```less
- hardware/ — UART, RS485, GPIO 제어 예제
- mqtt-bridge/ — Tornado + MQTT 이벤트 핸들러 구조
- multithreading/ — 멀티스레딩 + 뮤텍스 예제 (사운드키 인증)
- flutter_maintenance/ — Flutter 버전 충돌 해결 기록
```

#### 1. 시스템 안정성 최적화
```less
CPU 점유율 과부하(130%) 해결:
데이터 캡처 주기(Polling Rate) 최적화 및 로직 이원화를 통해 하드웨어 프리징 현상 방지

마이크 점유 충돌 방지:
사운드키 인증 시 스레드 간 자원 경합을 threading.Lock 및 Event Flag로 제어하여 데드락 해결
```

#### 2. 하드웨어 연동 및 환경 설정
```less
멀티 디스플레이 인터페이스: PySide6를 활용하여 Dual HDMI 환경에서 사용자/관리자용 터치 GUI 분리 및 제어

오디오 장치 식별 이슈: 동일 칩셋 사용 시 발생하는 장치 인식 오류를 리눅스 udev 규칙 설정을 통해 고유 식별값 부여
```

#### 3. 모바일 앱 운영 안정화
```less
Flutter 빌드 크래시 해결: 외부 라이브러리(mobile_scanner 등)와 MLKit 간의 의존성 충돌을 분석하여
엔진 버전 다운그레이드 및 라이브러리 고정으로 스토어 재배포 성공
```








