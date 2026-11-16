# Food Market Data Pipeline architecture

```text
KOSIS API ─────────┐
KAMIS HTML ────────┼─ raw storage → normalize → idempotent upsert
CJ IR PDF ─────────┘                         ↓
                                     quality results
                                             ↓
                                      CLI run report
```

원본 응답과 정제 데이터를 분리해 외부 스키마 변경과 처리 실패를 추적하고 재처리합니다. OCR, OpenDART, 웹 서버와 UI는 MVP 범위에서 제외합니다.


