# 미션 B5-1 평가항목 종합 정리 (`evaluation/`)

> **프로젝트**: [5-1-Mini-Redis_02](https://github.com/nick19850906-debug/5-1-Mini-Redis_02)  
> **핵심 주제**: 정보를 엄청 빠르게 찾아주는 작은 저장소 만들기 (해시맵 · 이중 연결 리스트 · 최소 힙 직접 구현 + LRU & TTL 통합 조율)

이 폴더는 **코디세이 B5-1 필수 미션 체크리스트(항목 1 ~ 항목 4, 총 17개 평가 질문)** 를 하나도 빠짐없이 개별적으로 해석·분석하고, 실제 구현 코드와 연결한 합리적인 모범 답변을 정리한 공간입니다.

---

## 평가항목 4대 영역 목차

| 영역 | 문서 파일 | 포함된 문항 수 | 핵심 평가 주제 |
| :--- | :--- | :---: | :--- |
| **항목 1** | [`item1_basic_features.md`](./item1_basic_features.md) | 5문항 | String 명령 6종, LRU 자동 제거, `INFO memory`, TTL/EXPIRE 관리, 표준 에러 처리 |
| **항목 2** | [`item2_data_structures.md`](./item2_data_structures.md) | 4문항 | 이중 연결 리스트 `O(1)` 구조, `djb2` 해시 함수 변환 과정, 체이닝 버킷 선택 이유, 로드 팩터 `0.75` 2배 확장 절차 |
| **항목 3** | [`item3_lru_ttl_flows.md`](./item3_lru_ttl_flows.md) | 5문항 | 해시맵+리스트 상호보완, `O(1)` LRU 원리, TTL 최소 힙 & Lazy Deletion, Eviction 흐름, `GET` 전체 흐름 |
| **항목 4** | [`item4_advanced_design.md`](./item4_advanced_design.md) | 3문항 | LFU 정책 전환 설계, 10만 건 확장 시 병목 및 개선안, 자료구조 오버헤드 포함 메모리 모델 및 공정 채점 보정 |

---

## 핵심 설계 질문 해결 요약 (사용자 설계 고민 해결)

> **질문**: "키는 하나인데 해시맵(데이터), 이중 연결 리스트(최근 사용 순서), 최소 힙(만료 시간)에 각각 관리하면 상태가 어긋나지 않을까?"

우리 프로젝트(`mini_redis/mini_redis.py`)는 다음 **3중 안전장치**로 상태 불일치를 원천 차단했습니다.

1. **관심사 분리 + `Entry` 단일 진입점**
   - 해시맵에는 단순 문자열 대신 `Entry(value, lru_node, expire_at)` 객체를 저장합니다.
   - 키를 해시맵에서 한 번만 찾으면 **실제 값(`value`)**, **LRU 리스트 노드 참조(`lru_node`)**, **만료 시각(`expire_at`)** 을 동시에 얻습니다.
2. **공통 삭제 메서드 `MiniRedis.delete_entry(key)`**
   - 명시적 삭제(`DEL`), 만료 삭제(`expire_if_needed` / `purge_expired`), 메모리 방출(`evict_if_needed`) 모두 반드시 `delete_entry(key)` 한 곳만 거칩니다.
   - `delete_entry` 내부에서 `LRU 리스트 노드 제거 → 해시맵 제거 → used_memory 차감`을 원자적으로 함께 처리합니다.
3. **최소 힙의 Lazy Deletion(지연 삭제)**
   - 힙은 중간 노드를 찾아 지우는 데 `O(n)`이 걸리므로, 키가 삭제되거나(`DEL`) 덮어쓰여도(`SET`, `EXPIRE` 재설정) 힙 내부의 옛 튜플 `(old_expire_at, key)`를 억지로 지우지 않습니다.
   - 대신 `purge_expired()`가 힙 루트에서 꺼낸 뒤 **`해시맵에 키가 살아 있고 entry.expire_at == pop된 expire_at 일 때만`** 진짜 만료로 인정해 삭제합니다.

---

## 빠른 자동 검증 명령어 (Windows CMD 기준)

```cmd
cd C:\Users\domod\5-1-Mini-Redis_02
python scripts\evaluate-mission.py
python -m unittest discover -s tests -t .
```
