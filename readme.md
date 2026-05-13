🛠️ IoT Hardware Control (Python)
실제 운영 제품(스마트도어, 무인보관함)의 하드웨어 통합 제어 및 시스템 최적화 사례

실제 운영 환경의 기술적 한계를 분석하고, 사용자 경험(UX) 개선을 위해 다중 디스플레이 인터페이스와 실시간 미디어 통신 구조를 설계 및 구현한 기록입니다.

## 다룬 하드웨어 / 통신 방식

| 항목 | 내용 |
|------|------|
| 통신 | UART(TTY), RS485, GPIO, Modbus RTU |
| 디바이스 | 솔레노이드 전자석, PIR 센서(내/외부), 가스/진동/불꽃/온습도 센서 |
| 플랫폼 | Raspberry Pi 4 |
| 백엔드 | Python Tornado (이벤트 핸들러), MQTT |
| 앱 | Flutter (iOS/Android 스토어 배포) |

## 폴더 구조

- hardware/ — UART, RS485, GPIO 제어 예제
- backend_tornado/ — Tornado + MQTT 이벤트 핸들러 구조
- multithreading/ — 멀티스레딩 + 뮤텍스 예제 (사운드키 인증)
- flutter_maintenance/ — Flutter 버전 충돌 해결 기록

## 이 리포지토리에서 보여주고 싶은 것

설계보다는 실제 운영 환경에서 만난 문제를 파악하고
원인을 찾아 해결한 과정을 중심으로 정리했습니다.

- CPU 130% 프리징 → 캡처 주기 제한 + 이원화 구조로 해결
- 멀티스레드 마이크 점유 충돌 → 뮤텍스 + 상태플래그로 해결
- Flutter iOS 빌드 크래시 → 엔진 버전 다운그레이드로 해결
- 동일 칩셋 오디오 장치 식별 불가 → udev 규칙으로 해결
