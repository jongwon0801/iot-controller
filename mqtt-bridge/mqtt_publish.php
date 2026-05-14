<?php
# -*- coding: utf-8 -*-
/**
 * MQTT 발행(Publish) 유틸 - 스마트도어 시스템
 *
 * 구조:
 *   모바일 앱 → HTTP POST → PHP API → mosquitto_pub CLI → Mosquitto 브로커
 *
 * 토픽 설계:
 *   Exam01/{code}/door               도어 제어 명령 (열기/닫기)
 *   Exam01/{code}/user/{user_id}     특정 사용자 대상 메시지
 *   Exam01/{code}/notice             공지사항 CRUD
 *   Exam01/{code}/schedule           일정 CRUD
 *   Exam01/{code}/message            메시지 CRUD
 *
 * 메시지 구조:
 *   { "request": "/Smartdoor/doorOpenAtAppProcess", "data": { ... } }
 *
 * 핵심 설계:
 *   - mosquitto_pub CLI를 exec() 으로 실행해 PHP에서 직접 브로커에 발행
 *   - QoS 2 (정확히 한 번 전달) 기본 적용
 *   - 발행 이력은 Logger에 저장 (topic, msg, result)
 */


// ── 설정 ─────────────────────────────────────────────────

$_lib['mqtt'] = [
    'host'   => getenv('MQTT_HOST')   ?: '127.0.0.1',
    'port'   => getenv('MQTT_PORT')   ?: 1883,
    'user'   => getenv('MQTT_USER')   ?: '',
    'passwd' => getenv('MQTT_PASSWD') ?: '',
];


// ── 토픽 생성 ─────────────────────────────────────────────

/**
 * 도어 제어 토픽 반환
 * Exam01/{code}/door
 */
function getDoorTopic(string $code): string {
    return "Exam01/{$code}/door";
}

/**
 * 특정 사용자 토픽 반환
 * Exam01/{code}/user/{user_id}
 */
function getUserTopic(string $code, int $user_id): string {
    return "Exam01/{$code}/user/{$user_id}";
}

/**
 * 공지사항 토픽 반환
 * Exam01/{code}/notice
 */
function getNoticeTopic(string $code): string {
    return "Exam01/{$code}/notice";
}

/**
 * 일정 토픽 반환
 * Exam01/{code}/schedule
 */
function getScheduleTopic(string $code): string {
    return "Exam01/{$code}/schedule";
}

/**
 * 메시지 토픽 반환
 * Exam01/{code}/message
 */
function getMessageTopic(string $code): string {
    return "Exam01/{$code}/message";
}


// ── MQTT 발행 유틸 ────────────────────────────────────────

/**
 * mosquitto_pub CLI를 통해 MQTT 브로커에 메시지 발행
 *
 * @param string $topic  발행 토픽
 * @param string $msg    JSON 인코딩된 메시지
 * @param int    $qos    QoS 레벨 (기본값 2: 정확히 한 번 전달)
 */
function mqtt_publish(string $topic, string $msg, int $qos = 2): void {
    global $_lib;

    putenv("LANG=ko_KR.UTF-8");
    setlocale(LC_ALL, 'ko_KR.utf8');

    $cmd = sprintf(
        "mosquitto_pub -h %s -p %d -u %s -P %s -t %s -m '%s' -q %d",
        escaphellarg($_lib['mqtt']['host']),
        (int)$_lib['mqtt']['port'],
        escaphellarg($_lib['mqtt']['user']),
        escaphellarg($_lib['mqtt']['passwd']),
        escaphellarg($topic),
        $msg,
        $qos
    );

    exec($cmd, $out, $status);

    // 발행 이력 로깅
    error_log(json_encode([
        'host'   => $_lib['mqtt']['host'],
        'topic'  => $topic,
        'msg'    => json_decode($msg, true),
        'result' => $out,
        'status' => $status,
    ], JSON_UNESCAPED_UNICODE));
}


// ── 도어 제어 ─────────────────────────────────────────────

/**
 * 앱에서 도어 열기 요청
 * 키오스크가 /Smartdoor/doorOpenAtAppProcess 핸들러로 처리
 */
function requestDoorOpen(string $code, int $user_id): void {
    $topic = getDoorTopic($code);
    $msg = json_encode([
        'request' => '/Smartdoor/doorOpenAtAppProcess',
        'user_id' => $user_id,
    ], JSON_UNESCAPED_UNICODE);

    mqtt_publish($topic, $msg);
}

/**
 * 앱에서 도어 닫기 요청
 */
function requestDoorClose(string $code, int $user_id): void {
    $topic = getDoorTopic($code);
    $msg = json_encode([
        'request' => '/Smartdoor/doorCloseAtAppProcess',
        'user_id' => $user_id,
    ], JSON_UNESCAPED_UNICODE);

    mqtt_publish($topic, $msg);
}


// ── 사용자 관리 ───────────────────────────────────────────

/**
 * 얼굴 정보 업데이트 요청
 * 키오스크 얼굴 인식 모델 갱신 트리거
 */
function requestFaceUpdate(string $code, int $user_id): void {
    $topic = getUserTopic($code, $user_id);
    $msg = json_encode([
        'request' => '/User/faceUpdateProcess',
        'user_id' => $user_id,
    ], JSON_UNESCAPED_UNICODE);

    mqtt_publish($topic, $msg);
}


// ── 공지사항 ──────────────────────────────────────────────

/**
 * 공지사항 등록 알림
 * 키오스크 화면에 즉시 반영
 */
function notifyNoticeJoin(string $code, array $notice): void {
    $topic = getNoticeTopic($code);
    $msg = json_encode([
        'request' => '/SmartdoorNotice/joinProcess',
        'data'    => $notice,
    ], JSON_UNESCAPED_UNICODE);

    mqtt_publish($topic, $msg);
}


// ── 실행 예제 ─────────────────────────────────────────────

// 도어 코드 'ABC123', 사용자 42번이 앱에서 문 열기 요청
requestDoorOpen('ABC123', 42);

// 사용자 얼굴 정보 업데이트
requestFaceUpdate('ABC123', 42);

// 공지사항 등록 후 키오스크에 즉시 반영
notifyNoticeJoin('ABC123', [
    'title'   => '엘리베이터 점검 안내',
    'content' => '내일 오전 10시 ~ 12시 엘리베이터 점검이 있습니다.',
]);
