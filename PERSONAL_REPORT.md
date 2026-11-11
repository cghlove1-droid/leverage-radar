# 개인용 오전 9시 보고서

사용 목적이 공개 상업 사이트에서 **본인만 보는 아침 보고서**로 변경되었습니다. 기존 `cghlove1-droid/leverage-radar`는 사용자의 요청대로 공개 상태로 유지합니다. 개인용 시세·보고서·캡처는 이 저장소나 Cloudflare Pages에 올리지 않습니다.

## 전달 및 예약

이 대화에 연결한 예약 작업이 매일 **한국시간 오전 9시**에 보고서 생성을 시작합니다. 자료 수집과 캡처에 시간이 걸리므로 수신 시각은 조금 늦을 수 있습니다. GitHub의 공개 배포 워크플로와 별개입니다. 기존 공개 웹용 수집·빌드의 재배포 권한 검사도 그대로 유지합니다.

작업은 `scripts/personal_report.py`로 FRED 공식 CSV와, 키가 있는 경우 Massive 개인용 API에서 자료를 읽습니다. 보고서는 HTML·PNG·Markdown·JSON으로 생성하며 출력 폴더는 반드시 공개 저장소 바깥이어야 합니다.

```sh
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
python scripts/personal_report.py --output /tmp/leverage-radar-personal --screenshot
```

수집 오류는 미확인으로 표시하며 가상 가격으로 대체하지 않습니다. 이전 정상 ETF 자료가 출력 폴더에 남아 있으면 이전 자료임을 표시하고, 갱신 실패 중에는 자체 심리지수를 표시하지 않습니다. 새 실행 환경에서 캐시가 유지된다고 보장하지 않습니다.

## 현재 실제 연결 상태

- **VIX / 하이일드 OAS:** FRED 공식 다운로드 `https://fred.stlouisfed.org/graph/fredgraph.csv?id=...`에서 실제 수집·검증·캡처 성공. 개인 비상업용 열람 용도이며 공개 재배포용 데이터가 아닙니다. 최종 관측일은 최신 완료 미국 거래일보다 늦게 발표될 수 있습니다. 수집일과 관측일을 구분합니다.
- **QQQ / TQQQ / SOXL:** 미연결. 개인용 Massive API 키가 없어서 실제 호출·정확성 대조는 아직 못 했습니다. 어댑터와 파생 계산은 모의 응답으로 테스트했습니다.
- **MDD / RSI14 / SMA200 / 자체 심리:** ETF 키 연결 후 계산합니다. 필수 지표가 없거나 지연되면 자체 점수는 미확인입니다.
- **CNN:** 공식 링크만 제공합니다. 크롤링하지 않습니다.

## 필요한 설정은 무료 개인용 API 키 1개

1. [Massive 주식 데이터](https://massive.com/stocks)에서 Stocks Basic 개인용 계정으로 가입합니다. 확인일 2026-11-11 기준 $0, 일별 종가, 2년 이력, 분당 5회 호출입니다. 가입 시점의 실제 조건을 다시 확인하세요.
2. API 키를 발급받습니다.
3. **이 예약 작업이 사용하는 클라우드 실행 환경의 Secrets/환경변수**에 `MASSIVE_API_KEY`로 등록합니다. GitHub 저장소의 Secrets와 별개이며, GitHub에만 넣으면 이 대화의 예약 작업에는 전달되지 않습니다.
4. 실제 연결 뒤 최종 거래일과 분할 전후 가격을 공급자 화면과 대조합니다.

키를 채팅·코드·공개 저장소에 넣지 마세요. 별도 상업용 재배포 계약은 이 개인용 모드에서 요구하지 않지만, 개인용 요금제 약관과 계정의 사용 자격은 적용됩니다. 유료 구독은 자동 신청하지 않습니다.

개인용 어댑터는 최근 720일만 요청하므로 무료 계정 범위 안에서 약 2년의 이력을 사용합니다. 3년·5년·설정 이후 MDD를 계산했다고 표시하지 않습니다. 세 종목 3번의 일별 API 호출을 사용합니다. 200거래일 이상이 없거나 최신 완료 세션 종가가 누락되면 정상 갱신으로 처리하지 않습니다.

## 권한 근거

- [Massive 개인용 약관](https://massive.com/legal/individuals-terms-of-service): 개인 비상업·비사업용 범위 내에서 지원 인터페이스로 개인용 앱과 분석을 만드는 것을 허용하며 실제 구매 권한·데이터 약관을 따라야 합니다.
- [Massive Stocks](https://massive.com/stocks): Basic 무료·EOD·2년 이력·5회/분, 개인/비전문가용. 공개 표시·재배포는 Business 계약 영역입니다.
- [FRED 이용약관](https://fred.stlouisfed.org/legal/): 개인 비상업용 이용·다운로드, 출처와 저작권 고지 유지. 상업적 재배포와 구분합니다. 시리즈 출처는 [VIXCLS](https://fred.stlouisfed.org/series/VIXCLS), [BAMLH0A0HYM2](https://fred.stlouisfed.org/series/BAMLH0A0HYM2)입니다.

보고서를 타인에게 배포하거나 공개 사이트로 옮기려면 공개 표시·재배포 권한을 다시 검토해야 합니다. 비공개 보고서를 만들었다고 기존 공개 사이트의 데이터 권한이 생기지 않습니다.
