# 5-1-Mini-Redis_02

파이썬 내장 `dict`, `set`, `collections`를 전혀 사용하지 않고 **이중 연결 리스트 · 체이닝 해시맵 · 최소 힙**을 직접 구현하여 **LRU 캐시 제거**와 **TTL 만료 관리**를 조율하는 CLI 기반 Mini Redis입니다.

---

## 실행 방법 (Windows CMD 기준)

```cmd
cd C:\Users\domod\5-1-Mini-Redis_02
python main.py
```

자동 검증 및 단위 테스트 실행:
```cmd
cd C:\Users\domod\5-1-Mini-Redis_02
python scripts\evaluate-mission.py
python -m unittest discover -s tests -t .
```

---

## 프로젝트 구조 (모듈 분리 + 상태 일관성 조율)

```text
5-1-Mini-Redis_02/
├── main.py                         # 루트 CLI 진입점
├── mini_redis/
│   ├── main.py                     # CLI 입력 / tokenize / execute / REPL 루프
│   ├── mini_redis.py               # Entry(value, lru_node, expire_at) 및 전체 상태 조율 (MiniRedis)
│   ├── string_commands.py          # SET, GET, DEL, EXISTS, DBSIZE, KEYS
│   ├── memory.py                   # maxmemory 설정, used_memory 계산, INFO memory, LRU 자동 제거
│   ├── ttl.py                      # EXPIRE, TTL, 만료 확인 및 힙 Lazy Deletion 청소
│   ├── errors.py                   # Redis 표준 에러 문구 및 OOMError 예외
│   ├── hashmap.py                  # 체이닝 해시맵 (djb2 해시, 로드 팩터 0.75 초과 시 2배 리사이즈)
│   ├── doubly_linked_list.py       # 이중 연결 리스트 (Node prev/next/data, 전 연산 O(1))
│   └── min_heap.py                 # 최소 힙 (완전 이진 트리 배열, peek O(1), push/pop O(log n))
├── evaluation/                     # B5-1 필수 평가항목(항목 1~4, 총 17문항) 심층 분석 및 모범 답변
│   ├── README.md                   # 전체 목차 및 상태 일관성 해결 요약
│   ├── item1_basic_features.md     # 항목 1: 기본 기능 · LRU · INFO memory · TTL · 에러 처리
│   ├── item2_data_structures.md    # 항목 2: 이중 연결 리스트 · djb2 해시 · 체이닝 · 0.75 리사이즈
│   ├── item3_lru_ttl_flows.md      # 항목 3: 해시맵+리스트 · O(1) LRU · TTL 힙 · Eviction · GET 흐름
│   └── item4_advanced_design.md    # 항목 4: LFU 전환 · 10만 건 병목/개선 · 오버헤드 모델 보정
├── docs/
│   ├── CONCEPTS.md                 # 비전공자 맞춤형 개념 가이드 (실생활 비유 + 퀴즈)
│   └── evaluation-script.md        # 퍼실리테이터 1:1 평가 발표 대본
├── scripts/
│   └── evaluate-mission.py         # 금지 자료형 AST 검사 + 필수 요구사항 12종 자동 채점기
└── tests/
    └── test_mini_redis.py          # 자료구조 3종 및 명령어/LRU/TTL/Lazy Deletion/에러 단위 테스트
```

---

## 평가항목 정리 바로가기 (`evaluation/`)

- [평가항목 전체 목차 (`evaluation/README.md`)](./evaluation/README.md)
- [항목 1: String 기본 동작 · LRU · INFO memory · TTL · 에러 처리](./evaluation/item1_basic_features.md)
- [항목 2: 이중 연결 리스트 `O(1)` · djb2 해시 · 체이닝 · 로드 팩터 0.75 리사이즈](./evaluation/item2_data_structures.md)
- [항목 3: 해시맵+리스트 역할 · `O(1)` LRU 원리 · TTL 힙 · Eviction · GET 흐름](./evaluation/item3_lru_ttl_flows.md)
- [항목 4: LFU 정책 전환 · 10만 건 병목/개선 · 오버헤드 포함 메모리 모델 보정](./evaluation/item4_advanced_design.md)
