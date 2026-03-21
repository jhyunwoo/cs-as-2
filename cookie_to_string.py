#!/usr/bin/env python3
"""
Cookie를 ASCII 문자열로 변환하는 도구
Attack Lab Phase 5에서 사용
"""

import sys

def cookie_to_ascii_hex(cookie):
    """
    16진수 cookie를 ASCII 문자열의 hex 표현으로 변환
    예: 0x59b997fa -> "35 39 62 39 39 37 66 61 00"
    """
    # 0x 접두사 제거
    if cookie.startswith('0x'):
        cookie = cookie[2:]
    
    # 8자리로 맞추기 (앞에 0 채우기)
    cookie = cookie.lower().zfill(8)
    
    if len(cookie) != 8:
        print(f"오류: cookie는 8자리 16진수여야 합니다. (입력: {cookie})")
        return None
    
    # 각 문자를 ASCII 코드로 변환
    ascii_bytes = []
    for char in cookie:
        if char in '0123456789':
            # '0'-'9'는 ASCII 0x30-0x39
            ascii_code = ord(char)
        elif char in 'abcdef':
            # 'a'-'f'는 ASCII 0x61-0x66
            ascii_code = ord(char)
        else:
            print(f"오류: 잘못된 16진수 문자: {char}")
            return None
        
        ascii_bytes.append(f"{ascii_code:02x}")
    
    # null 종료자 추가
    ascii_bytes.append("00")
    
    return " ".join(ascii_bytes)

def format_for_exploit(cookie):
    """Exploit 파일에 바로 사용할 수 있는 형식으로 출력"""
    hex_string = cookie_to_ascii_hex(cookie)
    if not hex_string:
        return
    
    print("=" * 70)
    print(f"Cookie: {cookie}")
    print("=" * 70)
    print()
    
    # 원래 값
    if cookie.startswith('0x'):
        cookie_clean = cookie[2:].lower().zfill(8)
    else:
        cookie_clean = cookie.lower().zfill(8)
    
    print("1. Cookie 문자열 (ASCII 형식):")
    print("-" * 70)
    print(f'   "{cookie_clean}"')
    print()
    
    print("2. Hex2raw 입력 형식:")
    print("-" * 70)
    print(f"   {hex_string}")
    print()
    
    print("3. Exploit 파일에 추가할 내용:")
    print("-" * 70)
    print(f"   /* Cookie string: {cookie_clean} */")
    print(f"   {hex_string}")
    print()
    
    # 각 바이트의 의미 설명
    print("4. 바이트별 설명:")
    print("-" * 70)
    bytes_list = hex_string.split()
    for i, (char, byte) in enumerate(zip(cookie_clean, bytes_list)):
        ascii_val = int(byte, 16)
        print(f"   '{char}' -> 0x{byte} (ASCII {ascii_val}, '{chr(ascii_val)}')")
    print(f"   null terminator -> 0x00")
    print()

def calculate_string_offset(buffer_size=40, num_gadgets=8):
    """
    문자열이 저장될 위치의 오프셋 계산
    """
    print("5. 오프셋 계산 (예상):")
    print("-" * 70)
    print(f"   버퍼 크기: {buffer_size} bytes")
    print(f"   가젯 수: {num_gadgets}")
    print(f"   각 가젯 주소: 8 bytes")
    print(f"   popq로 로드할 데이터: 8 bytes (예상)")
    print()
    
    offset = 8 * (num_gadgets + 1)  # gadgets + touch3 주소
    print(f"   예상 오프셋: {offset} bytes (0x{offset:x})")
    print(f"   Hex 형식: {offset:02x} 00 00 00 00 00 00 00")
    print()
    print("   ⚠️  주의: 실제 오프셋은 가젯 배치에 따라 다를 수 있습니다!")
    print("   GDB로 디버깅하면서 정확한 값을 확인하세요.")
    print()

def show_example():
    """예제 표시"""
    print("=" * 70)
    print("예제")
    print("=" * 70)
    print()
    print("Cookie가 0x59b997fa인 경우:")
    print()
    format_for_exploit("0x59b997fa")
    calculate_string_offset()

def main():
    print()
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "Cookie to ASCII String Converter" + " " * 21 + "║")
    print("║" + " " * 20 + "Attack Lab Phase 5" + " " * 28 + "║")
    print("╚" + "=" * 68 + "╝")
    print()
    
    if len(sys.argv) < 2:
        print("사용법: python3 cookie_to_string.py <cookie>")
        print()
        print("예제:")
        print("  python3 cookie_to_string.py 0x59b997fa")
        print("  python3 cookie_to_string.py 59b997fa")
        print()
        print("Cookie 값은 cookie.txt 파일에서 확인할 수 있습니다:")
        print("  cat cookie.txt")
        print()
        
        # 예제 표시
        show_example()
        sys.exit(1)
    
    cookie = sys.argv[1]
    format_for_exploit(cookie)
    calculate_string_offset()
    
    print("=" * 70)
    print("다음 단계:")
    print("=" * 70)
    print("1. find_gadgets.py로 필요한 가젯들을 찾으세요")
    print("2. 위의 hex 값들을 exploit.txt에 복사하세요")
    print("3. 가젯 주소와 오프셋을 올바르게 배치하세요")
    print("4. GDB로 테스트하세요")
    print()

if __name__ == "__main__":
    main()

