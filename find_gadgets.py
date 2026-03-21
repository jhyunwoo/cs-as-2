#!/usr/bin/env python3
"""
ROP 가젯 찾기 도구
rtarget의 디스어셈블리에서 유용한 가젯을 찾습니다.
"""

import sys
import re

def find_gadgets(disasm_file):
    """디스어셈블리 파일에서 가젯을 찾습니다."""
    
    try:
        with open(disasm_file, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"오류: {disasm_file} 파일을 찾을 수 없습니다.")
        print("먼저 'objdump -d rtarget > rtarget.d'를 실행하세요.")
        return
    
    # start_farm과 end_farm 사이의 라인만 추출
    in_farm = False
    farm_lines = []
    
    for i, line in enumerate(lines):
        if 'start_farm' in line:
            in_farm = True
            print(f"✓ start_farm 발견: {line.strip()}")
        elif 'end_farm' in line:
            in_farm = False
            print(f"✓ end_farm 발견: {line.strip()}\n")
            break
        elif in_farm:
            farm_lines.append((i, line))
    
    if not farm_lines:
        print("경고: farm 영역을 찾을 수 없습니다.")
        return
    
    print(f"가젯 팜 크기: {len(farm_lines)} 라인\n")
    print("=" * 70)
    print("유용한 가젯 검색 중...")
    print("=" * 70)
    
    # 찾을 가젯 패턴들
    gadget_patterns = [
        # popq 가젯들
        (r'([0-9a-f]+):\s+58\s+', 'popq %rax'),
        (r'([0-9a-f]+):\s+59\s+', 'popq %rcx'),
        (r'([0-9a-f]+):\s+5a\s+', 'popq %rdx'),
        (r'([0-9a-f]+):\s+5b\s+', 'popq %rbx'),
        (r'([0-9a-f]+):\s+5c\s+', 'popq %rsp'),
        (r'([0-9a-f]+):\s+5d\s+', 'popq %rbp'),
        (r'([0-9a-f]+):\s+5e\s+', 'popq %rsi'),
        (r'([0-9a-f]+):\s+5f\s+', 'popq %rdi'),
        
        # movq %rsp 가젯들
        (r'([0-9a-f]+):\s+48 89 e0', 'movq %rsp, %rax'),
        (r'([0-9a-f]+):\s+48 89 e7', 'movq %rsp, %rdi'),
        
        # movq 가젯들 (rax -> 다른 레지스터)
        (r'([0-9a-f]+):\s+48 89 c7', 'movq %rax, %rdi'),
        (r'([0-9a-f]+):\s+48 89 c1', 'movq %rax, %rcx'),
        (r'([0-9a-f]+):\s+48 89 c2', 'movq %rax, %rdx'),
        (r'([0-9a-f]+):\s+48 89 c6', 'movq %rax, %rsi'),
        
        # movl 가젯들 (32비트)
        (r'([0-9a-f]+):\s+89 c2', 'movl %eax, %edx'),
        (r'([0-9a-f]+):\s+89 c7', 'movl %eax, %edi'),
        (r'([0-9a-f]+):\s+89 d1', 'movl %edx, %ecx'),
        (r'([0-9a-f]+):\s+89 ce', 'movl %ecx, %esi'),
        (r'([0-9a-f]+):\s+89 c1', 'movl %eax, %ecx'),
        (r'([0-9a-f]+):\s+89 d7', 'movl %edx, %edi'),
        
        # lea 가젯들
        (r'([0-9a-f]+):\s+48 8d 04 37', 'lea (%rdi,%rsi,1),%rax'),
        (r'([0-9a-f]+):\s+48 8d 14 37', 'lea (%rdi,%rsi,1),%rdx'),
        
        # add 가젯들
        (r'([0-9a-f]+):\s+48 01 c7', 'add %rax, %rdi'),
        (r'([0-9a-f]+):\s+48 01 d7', 'add %rdx, %rdi'),
    ]
    
    found_gadgets = {}
    
    # 각 패턴을 검색
    for pattern, description in gadget_patterns:
        found_gadgets[description] = []
        
        for line_num, line in farm_lines:
            # 바이트 코드 부분만 추출
            match = re.search(pattern, line.lower())
            if match:
                addr = match.group(1)
                # retq(c3)로 끝나는지 확인
                if 'c3' in line or 'retq' in line:
                    found_gadgets[description].append((addr, line.strip()))
                else:
                    # 다음 몇 줄을 확인하여 c3가 있는지 확인
                    for offset in range(1, 5):
                        if line_num + offset < len(lines):
                            next_line = lines[line_num + offset].lower()
                            if 'c3' in next_line or 'retq' in next_line:
                                found_gadgets[description].append((addr, line.strip()))
                                break
    
    # 또한 바이트 시퀀스를 직접 검색 (함수 중간에 숨어있는 가젯)
    print("\n1. 명시적 가젯 (함수 시작 부분):")
    print("-" * 70)
    
    for desc, gadgets in found_gadgets.items():
        if gadgets:
            print(f"\n{desc}:")
            for addr, line in gadgets:
                print(f"  0x{addr}: {line}")
    
    # 바이트 시퀀스로 숨겨진 가젯 찾기
    print("\n\n2. 숨겨진 가젯 검색 (바이트 시퀀스 내부):")
    print("-" * 70)
    print("(명령어 중간에 숨어있는 가젯들)\n")
    
    byte_patterns = [
        ('48 89 c7 c3', 'movq %rax, %rdi; ret', [3, 4]),
        ('48 89 e0 c3', 'movq %rsp, %rax; ret', [3, 4]),
        ('89 c2 c3', 'movl %eax, %edx; ret', [2, 3]),
        ('89 d1 c3', 'movl %edx, %ecx; ret', [2, 3]),
        ('89 ce c3', 'movl %ecx, %esi; ret', [2, 3]),
        ('58 c3', 'popq %rax; ret', [1, 2]),
        ('5e c3', 'popq %rsi; ret', [1, 2]),
        ('48 8d 04 37 c3', 'lea (%rdi,%rsi,1),%rax; ret', [4, 5]),
    ]
    
    for byte_seq, desc, offsets in byte_patterns:
        print(f"{desc}:")
        hex_bytes = byte_seq.replace(' ', '')
        
        found = False
        for line_num, line in farm_lines:
            # 모든 공백 제거하고 16진수만 추출
            cleaned = re.sub(r'[^0-9a-f]', '', line.lower())
            
            # 바이트 시퀀스 찾기
            idx = cleaned.find(hex_bytes.replace(' ', ''))
            if idx >= 0:
                # 주소 추출
                addr_match = re.match(r'\s*([0-9a-f]+):', line.lower())
                if addr_match:
                    base_addr = int(addr_match.group(1), 16)
                    # 오프셋 계산
                    for offset in offsets:
                        actual_addr = base_addr + (idx // 2) + offset - len(hex_bytes.replace(' ', '')) // 2
                        print(f"  0x{actual_addr:x}: (offset +{offset-1} from function start)")
                        found = True
        
        if not found:
            print(f"  (발견되지 않음)")
        print()

def main():
    print("=" * 70)
    print("ROP 가젯 파인더 - Attack Lab Phase 5")
    print("=" * 70)
    print()
    
    if len(sys.argv) != 2:
        print("사용법: python3 find_gadgets.py <rtarget.d>")
        print()
        print("먼저 다음 명령어를 실행하세요:")
        print("  objdump -d rtarget > rtarget.d")
        print()
        sys.exit(1)
    
    find_gadgets(sys.argv[1])
    
    print("\n" + "=" * 70)
    print("다음 단계:")
    print("=" * 70)
    print("1. 위에서 찾은 가젯 주소들을 메모하세요")
    print("2. touch3의 주소를 확인하세요: grep 'touch3' rtarget.d")
    print("3. cookie.txt에서 cookie 값을 확인하세요")
    print("4. exploit.txt 파일을 작성하세요")
    print("5. ./hex2raw < exploit.txt > exploit-raw.txt")
    print("6. ./rtarget -i exploit-raw.txt")
    print()

if __name__ == "__main__":
    main()

