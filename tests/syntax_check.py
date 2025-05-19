#!/usr/bin/env python3

import ast
import sys

def check_syntax(file_path):
    """Check Python file syntax without executing it"""
    print(f"Checking syntax for: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            source = file.read()
        ast.parse(source)
        print(f"✅ Syntax is valid for {file_path}")
        return True
    except SyntaxError as e:
        print(f"❌ Syntax error in {file_path}:")
        print(f"  Line {e.lineno}, Column {e.offset}: {e.text}")
        print(f"  {e}")
        return False
    except Exception as e:
        print(f"❌ Error checking {file_path}: {str(e)}")
        return False

def main():
    """Main function to check syntax of specified files"""
    if len(sys.argv) < 2:
        print("Usage: python syntax_check.py file1.py file2.py ...")
        sys.exit(1)
    
    files = sys.argv[1:]
    all_valid = True
    
    for file_path in files:
        if not check_syntax(file_path):
            all_valid = False
    
    if all_valid:
        print("\n✅ All files have valid syntax!")
        sys.exit(0)
    else:
        print("\n❌ Some files have syntax errors.")
        sys.exit(1)

if __name__ == "__main__":
    main()
