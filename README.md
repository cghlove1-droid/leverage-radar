# LEVERAGE RADAR

QQQ · TQQQ · SOXL 일별 분할 조정 종가, 누적 고점 대비 낙폭, 기간 MDD, VIX, 하이일드 스프레드, Wilder RSI(14), SMA200 이격도, 자체 심리지수, 분할매수 계산기를 제공하는 한국어 정적 사이트입니다.

**현재 상태: DEMO / DATA NOT CONNECTED.** API 키·데이터 계약·GitHub/Cloudflare 계정 연결이 제공되지 않았습니다. 실제 시세 수집 성공 또는 운영 배포를 완료했다고 주장하지 않습니다. 데모 가격은 수학식으로 생성한 가상 값입니다. 상세 결과는 `TEST_REPORT.md`를 확인하세요.

## 1. 가장 먼저 데이터 권한 확보

[DATA_LICENSES.md](DATA_LICENSES.md)의 공식 근거와 체크 항목을 읽으세요. 무료 개인용 API, Yahoo 비공식 수집, CNN 크롤링은 사용하지 않습니다.

- ETF: Massive Business에 공개 상업 웹 표시와 **원본 JSON/과거 이력 재배포** 허가를 문의합니다. 계약상 가능한 상품·범위와 2010년 이후 전체 이력 접근을 확인합니다. 별도 거래소 계약이 필요할 수 있습니다.
- VIX: CBOE/FRED 사용 범위 및 공개 재배포 허가를 확인합니다.
- 하이일드 스프레드: ICE Data Indices 서면 허가를 확보합니다.
- CNN 지수는 공식 페이지 링크만 제공합니다.

키만 발급받아서는 공개용 실데이터를 활성화할 수 없습니다. 계약하지 않은 지표는 미연결로 두어도 됩니다. 이 경우 자체 심리지수도 미확인으로 표시합니다. 라이선스는 운영자 확인 기록으로 관리하며 프로그램이 계약서를 법적으로 검증하지는 않습니다.

## 2. 로컬에서 데모 실행

Python 3.12와 Node.js 22 이상을 설치하세요. 터미널에서 이 README가 있는 폴더로 이동합니다.

```sh
python -m venv .venv
# macOS/Linux:
. .venv/bin/activate
# Windows PowerShell은 위 줄 대신: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m http.server 8000
```

브라우저에서 http://localhost:8000 을 여세요. 모듈과 JSON을 읽으므로 HTML 더블클릭 대신 HTTP 서버를 사용합니다. 외부 JS/CDN 의존성이 없습니다. 금액·수량 계산은 브라우저 안에서만 수행합니다. 배포물만 보려면 `python scripts/build.py` 후 `python -m http.server 8000 --directory dist`로 실행합니다.

## 3. GitHub 저장소 만들기

1. GitHub 계정을 만들고 New repository에서 저장소를 생성합니다. 원본 이력 재배포 범위를 고려하면 **비공개 저장소 권장**입니다.
2. 이 프로젝트 전체를 올립니다. 숨김 `.github` 폴더도 포함해야 합니다. `dist`, `.venv`, API 키, `.env`는 올리지 마세요. GitHub 웹 업로드가 숨김 폴더를 누락하면 GitHub Desktop의 Add local repository → Publish repository를 사용하세요.
3. 기본 브랜치는 `main`으로 설정합니다.
4. Settings → Actions → General → Workflow permissions에서 Read and write permissions를 허용합니다. 브랜치 보호 규칙이 bot의 직접 push를 금지하면 별도 갱신 브랜치/PR 운영이 필요하며 현재 워크플로는 직접 커밋 방식입니다.

## 4. 공급자 및 권한 설정

### 방법 A: Massive 직접 연결

계약과 키가 준비되면 `config/licenses.json`의 `prices` 항목을 수정합니다.

```json
{
  "provider": "massive",
  "public_display": true,
  "raw_redistribution": true,
  "reference": "approved-etf-public-json-contract",
  "attribution": "계약에서 요구한 실제 공개 출처 문구",
  "valid_until": "2027-11-10"
}
```

위 날짜·문구는 예시입니다. 실제 허가 조건을 입력하세요. 파일의 다른 지표 항목은 유지합니다.

GitHub Settings → Secrets and variables → Actions에서:

| 종류 | 이름 | 값 |
|---|---|---|
| Variables | `DATA_PROVIDER` | `massive` |
| Secrets | `MASSIVE_API_KEY` | 계약한 Massive API 키 |
| Secrets | `FRED_API_KEY` | FRED API 키 (허가한 외부 지표에만 필요) |

VIX/스프레드는 각각 해당 `vix`/`hySpread` 권한 항목을 실제 계약에 맞게 설정합니다. `provider: "fred"`를 사용합니다. FRED 계정 → [API 키 신청](https://fred.stlouisfed.org/docs/api/api_key.html)에서 키를 발급합니다. **이 키는 CBOE/ICE 권한을 대신하지 않습니다.** 키는 채팅이나 프런트엔드에 입력하지 마세요.

### 방법 B: 기존 계약 공급자의 HTTPS JSON

`DATA_PROVIDER=licensed_json`, Secrets `MARKET_DATA_URL`, 필요 시 `MARKET_DATA_TOKEN`을 설정합니다. `prices.provider`도 `licensed_json`으로 변경합니다. URL은 HTTPS이며 리다이렉트하지 않아야 합니다. Bearer 인증만 지원합니다. 공급자 전용 스키마인 경우 어댑터를 추가해야 하며 어떤 API든 자동 호환되는 것은 아닙니다.

엔드포인트는 최소 200개의 **연속된 공통 거래일** 전체 이력과 다음 구조를 반환해야 합니다. 아래 값은 형식 예시이며 실데이터가 아닙니다.

```json
{
  "demo": false,
  "adjustment": "split_only",
  "prices": [
    {"date":"2026-11-06","QQQ":600.0,"TQQQ":75.0,"SOXL":40.0},
    {"date":"2026-11-09","QQQ":605.0,"TQQQ":76.5,"SOXL":41.2}
  ],
  "indicators": {
    "vix":{"value":20.5,"date":"2026-11-09"},
    "hySpread":{"value":3.2,"date":"2026-11-06"}
  }
}
```

예시는 2행으로 축약했습니다. 숫자는 JSON number이며 문자열·NaN은 거부합니다. 종가 분할 조정 여부는 계약과 공급자 문서로 검증해야 합니다. 종가로 RSI를 계산하므로 배당 조정 데이터를 섞지 마세요. 외부 지표도 이 JSON에 넣으려면 해당 지표 권한 항목의 `provider`를 `licensed_json`으로 설정합니다. ETF는 Massive, 지표는 FRED 조합도 지원합니다.

## 5. 수동 수집과 검증

1. Actions → Daily market data update → Run workflow를 누릅니다.
2. 실행 로그의 Tests, Fetch authorized data, Verify public build, Commit 단계가 성공하는지 확인합니다.
3. `data/market.json`의 `demo:false`, `source`, `adjustment:split_only`, `last_session`, `updated_at`, 지표 관측일을 확인합니다. `data/status.json`은 마지막 시도·예상 거래일·안전한 오류 코드를 기록합니다.
4. 가격은 공급자 공식 화면의 같은 조정 기준 종가와 대조하세요. 최소 3개 날짜와 분할 전후를 확인해야 실사용 검증이 끝납니다. 이 대조는 현재 키가 없어 수행하지 못했습니다.
5. 사이트에서 실제 연결 상태가 최신인지 확인합니다. 미연결 지표를 0으로 취급하지 않습니다.

자동 실행은 평일 **UTC 23:15 = 다음 날 한국시간 08:15(화~토)**입니다. 동부시간 여름 19:15 / 겨울 18:15로 정규장 종료 뒤입니다. GitHub 예약은 지연되거나 비활성 저장소에서 중단될 수 있습니다. 미국 휴장일은 거래 달력에 따라 같은 종가를 유지합니다. 전일 대비 내용이 같으면 market.json과 마지막 성공 갱신 시각을 바꾸지 않고 확인 시각만 status.json에 남깁니다. 외부 지표가 새로 발표되면 휴장일에도 그 지표는 갱신할 수 있습니다.

가격 수집/검증 실패는 market.json을 보존하고 status.json을 커밋한 뒤 워크플로를 실패 처리합니다. 지표 하나만 실패하면 해당 지표를 미확인으로 저장하고 가격은 갱신합니다. 실패 응답·URL·토큰을 공개 로그에 기록하지 않습니다. 빌드 시 권한 만료/미승인이면 배포가 차단됩니다. 기존 배포의 원본 파일 삭제까지 자동으로 수행하지 않습니다.

## 6. Cloudflare Pages 연결

1. Cloudflare 계정 → Workers & Pages → Create → Pages → Connect to Git을 선택합니다.
2. GitHub 계정 연결을 승인하고 이 저장소 접근을 허용합니다. 프로덕션 브랜치 `main`을 선택합니다.
3. Framework preset: None. Build command: `pip install -r requirements.txt && python scripts/build.py`. Build output directory: **`dist`**. Root directory는 프로젝트가 저장소 최상위면 비워둡니다.
4. Build environment variable `PYTHON_VERSION=3.12`를 설정합니다. 공급자 키는 Cloudflare에 넣지 않습니다. 수집은 GitHub Actions에서만 합니다.
5. Save and Deploy를 누릅니다. 생성된 `*.pages.dev` 주소를 엽니다. 초기 배포는 DEMO가 정상입니다.
6. GitHub Actions가 JSON을 커밋한 뒤 Cloudflare의 새 배포가 성공하는지 확인합니다. 자동 빌드를 끈 경우 다시 켜세요. 사이트의 최종 거래일·갱신 시각이 새 JSON과 일치해야 합니다.

`dist/`에는 HTML/CSS/JS·공개 JSON·보안 헤더만 복사됩니다. 스크립트·테스트·라이선스 내부 참조·API 키는 포함하지 않습니다. **market.json은 누구나 다운로드할 수 있습니다.** 배포 비용/빌드 할당량/도메인은 각 계정 요금제를 확인하세요. 현재 GitHub 저장소 생성과 Cloudflare 실배포는 계정 연결이 없어 미실행입니다.

## 계산 정의와 상태

- Massive는 2010-03-11부터 조회하고 세 ETF의 공통 거래일을 사용합니다. 종가는 주식분할 조정·배당 미조정입니다. 배당 조정/총수익 기준과 MDD가 다릅니다.
- Drawdown = `(종가 / 해당 일까지 전체 제공 이력의 최고 종가 - 1) × 100`. 선택한 1/3/5년은 최종 거래일에서 달력 연도로 역산합니다. 기간 MDD는 선택 구간 내 drawdown 최솟값입니다. 최고점은 기간 시작에서 초기화하지 않습니다. “전체”는 공급자가 제공한 공통 이력 전체이며 QQQ 설정 이후 전체를 뜻하지 않습니다.
- Wilder RSI(14), QQQ 단순이동평균 200일 및 이격도 `(현재가/SMA200-1)×100`. 불변 가격 RSI는 중립 50으로 정의합니다.
- 자체 심리: RSI, `50+이격도×2`, `100+QQQ낙폭×3`, `100-(VIX-10)×3`, `100-(HY스프레드-2)×20`을 각각 0~100으로 제한 후 동일 가중 평균·반올림. HY는 % 단위(3.2 = 3.2%, 320bp). 0=공포, 100=탐욕. CNN과 무관하고 검증된 투자 신호가 아닙니다.
- 최신 ETF 종가가 최근 완료 세션과 다르면 미확인. VIX/스프레드는 관측일 기준 최대 **3개 NYSE 세션 지연**을 허용하고 날짜를 노출합니다. 이를 넘거나 하나라도 누락·권한 만료이면 자체 점수를 표시하지 않습니다. 이 허용은 공급자의 발표 시각 보증이 아닙니다.
- XNYS 달력으로 휴장·서머타임·조기 폐장을 처리합니다. 브라우저 달력 범위 2020~2031년. 범위 밖은 미확인입니다. 임시 휴장 공지가 나오면 달력 패키지를 갱신하고 `python scripts/calendar_export.py`를 실행·커밋하세요. 미국 ETF 세션에 XNYS 공통 달력을 사용합니다.
- 매수금액은 **USD**, 또는 소수점 수량(주). 총투입금=가격×수량 합, 평단=총투입금/총수량, 손익률=(현재가/평단−1)×100, 원금회복 상승률=max(0,(평단/현재가−1)×100). 수수료·세금·환율·배당 제외.
- CSV는 `date,QQQ,TQQQ,SOXL` 순서, ISO 날짜, 양수 숫자, 중복 없는 최소 2행. 정렬 후 브라우저에서만 표시하며 지표·출처의 진위를 보증하지 않습니다. 공식 API 수집은 추가로 거래일 연속성과 최소 이력을 검증합니다.

## 테스트 명령

```sh
python -m unittest discover -s tests -v
node --test tests/core.test.mjs
python scripts/build.py
```

브라우저 회귀 테스트(개발 선택 사항): `python -m pip install playwright==1.62.0`, `python -m playwright install chromium`, 서버를 위의 8000 포트로 실행한 후 `python tests/browser_smoke.py`. 이 테스트는 모의 연결 응답을 브라우저에서만 사용하며 배포 JSON을 변경하지 않습니다.

실데이터 검증 전에는 데모/미확인 표시를 제거하지 마세요. 레버리지 ETF의 장기 성과는 기초지수 수익률의 단순 3배와 다릅니다. 정보 제공용이며 투자 조언이 아닙니다.
