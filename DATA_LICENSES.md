# 데이터 라이선스 검토

확인일: 2026-11-10. 아래는 확인한 공개 약관과 이 프로젝트의 운영 조건입니다. 사용자 명의의 계약·허가는 제공되지 않았으므로 **현재 공개용 실데이터는 모두 미연결**입니다. 가격·VIX·ICE 스프레드를 자동으로 무료 재배포할 수 있다고 보장하지 않습니다.

| 항목 | 공식 근거 | 확인 결과 / 활성화 조건 |
|---|---|---|
| QQQ/TQQQ/SOXL | [Massive 약관](https://massive.com/terms), [사업용 약관](https://massive.com/legal/businesses-terms-of-service) 2.1, 2.2, 2.5, 6 | 개인용 요금제는 사업용 허가가 아님. 사업용도 구매 권한·Order Form·제3자 거래소 계약에 종속됨. 공개 웹 표시, 파생지표, 원본 JSON 전달, 저장소/배포 캐시 보관, 과거 데이터 제공 기간에 대한 서면 허가 필요. **Business 구독만으로 무조건 허용되는 것이 아님.** |
| 분할 조정 방식 | [Massive Daily Aggregates](https://massive.com/docs/rest/stocks/aggregates/custom-bars) | `adjusted=true`는 주식분할 조정. 일별 `c` 종가를 사용. 배당 재투자를 반영한 총수익/배당 조정 종가가 아님. |
| VIXCLS | [FRED 시리즈](https://fred.stlouisfed.org/series/VIXCLS), [FRED 약관](https://fred.stlouisfed.org/legal/) | 시리즈는 `Copyrighted: Citation Required`, CBOE 소유. 약관의 내부 상업용/보고서 허용을 익명 공개 정적 JSON 재배포 허가로 확대 해석하지 않음. CBOE 및 FRED에 해당 사용 범위 확인 후 활성화. 출처·관측일·요구 저작권 고지 필수. |
| BAMLH0A0HYM2 | [FRED 시리즈](https://fred.stlouisfed.org/series/BAMLH0A0HYM2) | `Copyrighted: Pre-Approval Required`. “Reproduction ... in any form is prohibited except with the prior written permission of ICE Data Indices.” ICE 서면 허가 필수. FRED 무료 키와 별개. |
| CNN Fear & Greed | [CNN 공식 페이지](https://www.cnn.com/markets/fear-and-greed) | 크롤링·비공식 API·수치 복제 없음. 공식 링크만 제공. 자체 지수는 CNN과 무관. |
| 사용자 CSV | 사용자 보유 파일 | 브라우저 내부 처리만 수행. 출처·권한 미검증으로 표시하며 자동 실데이터 연결로 취급하지 않음. |

## 공급자에게 확인할 내용

“익명 사용자가 접근하는 상업 웹사이트에서 QQQ/TQQQ/SOXL의 일별 분할 조정 종가 전체 이력, VIX, ICE BofA US HY OAS를 차트와 지표로 표시하려고 합니다. Cloudflare Pages의 공개 `data/market.json`을 통해 원본 가격이 다운로드 가능하며 GitHub 저장소 및 Git 이력에 저장됩니다. MDD·RSI·SMA·자체 심리지수로 가공합니다. 이 사용, 과거 이력, 캐시/CDN 보관, 파생 데이터 및 원본 재배포를 허용하는 계약과 필수 출처 표기를 알려 주세요.”

공개 GitHub 저장소의 **Git 이력도 원본 데이터 재배포**입니다. 비공개 저장소를 사용해도 Pages의 JSON은 공개입니다. 공급자가 화면 표시만 허용하고 원본 배포는 금지하면 이 정적 구조로 활성화하지 마세요. 별도 계약 또는 서버에서 원본 노출을 통제하는 구조가 필요합니다.

## 권한 설정의 의미

`config/licenses.json`은 허가를 발급하는 파일이 아닙니다. 확보한 계약을 운영자가 확인했다는 기록입니다. `public_display`, `raw_redistribution` 둘 다 true이고, `reference`, `attribution`, 유효한 `valid_until`이 있어야 수집·빌드가 진행됩니다. 계약서 자체나 비공개 계약번호·개인정보를 커밋하지 말고 `reference`에는 비민감 내부 참조명만 쓰세요. 실제 계약 범위·갱신·종료에 따른 데이터 삭제는 운영자가 관리해야 합니다. 기존 Cloudflare 배포는 라이선스 파일 수정만으로 삭제되지 않습니다. 계약 종료 시 사이트와 저장 이력을 계약에 맞게 정리해야 합니다.
