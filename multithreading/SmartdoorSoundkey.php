<?php
class SmartdoorSoundkey extends Component {
    // 1. 사운드키 발행 및 SMS 전송 (Business Logic)
    function joinProcess($json) {
        $data = parseJson($json);

        // 권한 확인 및 스마트도어 소유자 검증 (생략)
        
        // 중복 발행 방지 및 DB 저장
        if (!$this->saveAll($data)) return false;

        // 보안을 위해 PK를 인코딩하여 재생 URL 생성
        $secureId = base64_encode("skey" . $this->__pkValue__);
        $playUrl = "https://api.your-service.com/soundkey?id=" . urlencode($secureId);

        // SMS Gateway 연동 (사운드키 재생 링크 발송)
        $ums = new Ums();
        return $ums->sendSms([
            'to' => $this->handphone,
            'msg' => "[스마트도어] 사운드키가 발행되었습니다. 클릭 시 재생: " . $playUrl
        ]);
    }

    // 2. 사운드키 유효성 검증 및 상태 관리
    function play($encodedId) {
        $pkValue = $this->decodeAndVerify($encodedId);
        if (!$pkValue) return false;

        $this->getData($pkValue);

        // 만료 시간 및 상태 체크 (1: 대기, 2: 사용중, 3: 만료)
        if ($this->status == 3 || $this->stopDate < now()) {
            return $this->error("만료된 키입니다.");
        }

        // 첫 접근 시 사용중(2)으로 상태 변경
        if ($this->status == 1) {
            $this->status = 2;
            $this->save();
        }

        return $this->toJson();
    }

    // 3. 파이썬 엔진 연동 및 WAV 스트리밍 (System Integration)
    function wav($encodedId) {
        $pkValue = $this->decodeAndVerify($encodedId);
        $this->getData($pkValue);

        // 음파로 변환할 데이터 조합 (비밀번호|만료일|전화번호)
        $payload = "{$this->passwd}|{$this->stopDate}|{$this->handphone}";

        // Python 주파수 생성 엔진 호출 (Inter-process Communication)
        // 엔진은 주파수 변환 후 Base64로 WAV 바이너리 반환
        $command = "/usr/bin/python3 /path/to/soundkey.py " . escapeshellarg($payload);
        exec($command, $output);
        $base64Wav = implode('', $output);

        // 오디오 바이너리 직접 응답 (Direct Streaming)
        if (ob_get_level()) ob_end_clean();
        header('Content-Type: audio/wav');
        header('Cache-Control: no-store');
        echo base64_decode($base64Wav);
        exit();
    }

    // 보안 디코딩 헬퍼
    private function decodeAndVerify($id) {
        $decoded = base64_decode(urldecode($id));
        return (strpos($decoded, 'skey') === 0) ? (int)substr($decoded, 4) : false;
    }
}
