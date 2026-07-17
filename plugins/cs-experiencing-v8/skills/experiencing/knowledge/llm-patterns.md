# LLM API·프롬프트 패턴 학습

cs-experiencing 학습 INDEX가 참조하는 본문 모음. 신규 학습은 끝에 append.

### 87. 구조화 JSON 추출 태스크에는 소형 LLM + 출력 토큰 상한 축소가 충분하다 (2026-06-30)
<!-- tier: tactical -->

- **상황**: voice-order API의 응답 지연 문제 해결 중 (gpt-5.5, max_completion_tokens=1000 사용)
- **발견**: 음식/커피 이름 매칭처럼 '후보 목록에서 선택 → 고정 포맷 JSON 반환'만 하는 태스크에서 대형 모델은 과도하다. gpt-4o-mini + 출력 토큰 200으로 교체했을 때 속도 3-5배 개선, 품질 동일.
- **교훈**: LLM 호출 설계 시 "패턴 매칭 → 고정 포맷 JSON 출력" 태스크라면 사용 가능한 최소 모델 + 예상 최대 출력 길이로 토큰 상한을 설정한다. 대형 모델은 자유 생성·다단계 추론이 필요한 경우에만 사용한다.
- **근거**: `route.ts line 84-89: model "gpt-5.5" → "gpt-4o-mini", max_completion_tokens 1000 → 200` (2026-06-30 세션, 속도 3-5배 개선 확인)

### 88. 단일 LLM 호출에서 다중 엔티티를 동시 추출하여 복합 발화를 처리한다 (2026-06-30)
<!-- tier: principle -->

- **상황**: "알탕에 카페라테아이스" 같은 rice+coffee 복합 발화가 rice만 추출되고 coffee는 버려지는 UX 문제 발견
- **발견**: rice/restaurant step의 system prompt에 coffeeMatched·coffeeTemp 보조 필드를 추가하자, 기존 GPT 호출 1회로 두 엔티티를 동시 추출할 수 있었다. 별도 coffee step 호출 없이 confirm으로 즉시 이동 가능.
- **교훈**: 사용자 발화에 여러 엔티티가 섞일 가능성이 있는 step은 system prompt JSON 스키마에 보조 엔티티 필드를 미리 정의한다. LLM 추가 호출 없이 응답 스키마 확장만으로 복합 입력을 처리할 수 있다 — per-invocation overhead >> per-token cost이므로 스키마 확장이 항상 추가 호출보다 싸다.
- **근거**: `buildSystemPrompt() rice step: coffeeMatched/coffeeTemp 필드 추가 → voice-order-bot.tsx coffeeResult로 즉시 confirm 이동` (app/api/voice-order/route.ts + components/voice-order-bot.tsx, 2026-06-30)

### 104. OpenAI 추론형(reasoning-tier) 모델은 temperature 기본값(1) 외 다른 값을 거부한다 (2026-07-11)
<!-- tier: tactical, error-ref: ERR-2026-07-11-002 -->

- **상황**: meokgo-study `/my` 페이지의 "AI 추천받기" 버튼이 항상 실패 배너를 띄우는 버그를 QA 중 발견하고 원인 조사.
- **발견**: `app/api/ai-recommend/route.ts`가 `model: "gpt-5.5"`(추론형 모델)와 `temperature: 0.8`을 함께 OpenAI Chat Completions 요청에 넣고 있었는데, 추론형 모델은 기본값(1) 이외의 temperature를 거부해 업스트림이 400을 반환하고 라우트가 이를 502로 사용자에게 그대로 노출했다. `temperature` 라인을 제거하자 정상 동작 확인.
- **교훈**: OpenAI API 호출 시 사용 모델이 추론형(reasoning-tier)인지 먼저 확인하고, 추론형이면 temperature/top_p 등 샘플링 파라미터를 아예 보내지 않는다. 502/400 에러 발생 시 모델-파라미터 호환성부터 의심한다. (skeptic verifier DOWNGRADE — 벤더가 향후 이 제약을 바꿀 수 있는 API/모델-버전 종속 사실이라 principle이 아닌 tactical로 판정)
- **근거**: `"Unsupported value: 'temperature' does not support 0.8 with this model. Only the default (1) value is supported."` 에러 확인 → `temperature: 0.8` 라인 제거 → 재현 테스트로 정상 추천 응답 생성 확인.
