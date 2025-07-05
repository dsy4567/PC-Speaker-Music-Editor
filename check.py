#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import sys

def validate_line(line, line_num):
    """验证单行格式并计算总和"""
    # 正则表达式匹配 x(*y,*z) 格式
    pattern = r'([+-]?\d+(?:\.\d+)?)\(\*([+-]?\d+(?:\.\d+)?),\*([+-]?\d+(?:\.\d+)?)\)'
    matches = re.findall(pattern, line)
    
    # 检查格式错误
    if "(*" in line and not matches:
        return f"Line {line_num}: Format error - '{line.strip()}' contains parentheses but invalid syntax"
    
    # 计算总和
    total_y = 0.0
    total_z = 0.0
    for x, y, z in matches:
        try:
            total_y += float(y)
            total_z += float(z)
        except ValueError:
            return f"Line {line_num}: Format error - '{line.strip()}' contains non-numeric values"
    
    # 检查总和是否为4（考虑浮点精度）
    total = total_y + total_z
    if not (3.999 < total < 4.001):  # 允许0.001的误差
        return f"Line {line_num}: Sum error - {total:.3f} ≠ 4 in '{line.strip()}'"
    
    return None

def main(filename):
    """主函数：处理文件并验证每行"""
    results = []
    with open(filename, 'r', encoding='utf-8') as file:
        for line_num, line in enumerate(file, 1):
            line = line.strip()
            # 跳过空行和注释行
            if not line or line.startswith('#') or line.startswith('//'):
                continue
            # 验证行格式
            error = validate_line(line, line_num)
            if error:
                results.append(error)
    
    # 输出结果
    if results:
        print("Validation errors found:")
        for error in results:
            print(error)
        sys.exit(1)
    else:
        print("All lines are valid and sum to 4")
        sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <filename.txt>")
        sys.exit(1)
    main(sys.argv[1])
