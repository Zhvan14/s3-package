import sys
import re
import os

def evaluate_expression(expr_string, variables, last_input):
    expr_string = expr_string.strip()
    expr_string = expr_string.replace('((input))', str(last_input))
    def var_replace(match):
        var_name = match.group(1)
        if var_name in variables:
            return str(variables[var_name])
        else:
            raise Exception(f"Undefined variable '{var_name}'")
    processed_expr = re.sub(r'\(([a-zA-Z_][a-zA-Z0-9_]*)\)', var_replace, expr_string)
    if "++" in processed_expr:
        parts = [p.strip() for p in processed_expr.split("++")]
        return ''.join(parts)
    if not re.fullmatch(r'[0-9+\-*/().\s]+', processed_expr):
        raise Exception("Invalid characters or syntax in arithmetic expression.")
    try:
        result = eval(processed_expr, {"__builtins__": None}, {})
        if isinstance(result, (int, float)):
            return result
        else:
            raise Exception("Expression did not evaluate to a valid number.")
    except Exception as e:
        raise Exception(f"Could not evaluate expression: {str(e)}")

def display_help():
    print("""
S Language Commands:
  func <function_name>         Function definition. Ends with end. Call with <function_name> on a line.
  <function_name>              Calls a function previously defined.
  write <text>                 Prints literal text.
  write (variable_name)        Prints the value of a variable.
  write ((input))              Prints last input value.
  write (<expression>)         Prints result of arithmetic or string expr.
                               Operators: +, -, *, /, ++ (concatenation)
  writeinput <prompt>          Prompts for user input.
  variable_name <value>        Assigns a literal value.
  variable_name ((input))      Assigns last input to variable.
  variable_name (<expr>)       Assigns expr result to variable.
  img "image_url"              Prints image URL (CLI only).
  if var = "value" then ... end   Conditional block, executes code inside if var matches value.
  $                            Comments after $ are ignored.
""")

def parse_line(line):
    line = line.split('$')[0].strip()
    if not line:
        return None
    if line.strip().lower() == "end":
        return ("end",)
    m = re.match(r'^func\s+<([a-zA-Z_][a-zA-Z0-9_]*)>$', line)
    if m:
        return ('func_def', m.group(1))
    m = re.match(r'^<([a-zA-Z_][a-zA-Z0-9_]*)>$', line)
    if m:
        return ('call_func', m.group(1))
    m = re.match(r'^if\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*"([^"]*)"\s*then$', line)
    if m:
        return ('if', m.group(1), m.group(2))
    m = re.match(r'^writeinput\s+(.*)$', line)
    if m:
        return ('writeinput', m.group(1))
    m = re.match(r'^img\s+"([^"]+)"$', line)
    if m:
        return ('img', m.group(1))
    if re.match(r'^write\s+\(\(input\)\)$', line):
        return ('write_system_input',)
    m = re.match(r'^write\s+\((.+)\)$', line)
    if m:
        content = m.group(1).strip()
        if re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_]*', content):
            return ('write_var', content)
        else:
            return ('write_expr', content)
    m = re.match(r'^write\s+(.*)$', line)
    if m:
        return ('write_literal', m.group(1))
    m = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s+(.*)$', line)
    if m:
        var, val = m.group(1), m.group(2).strip()
        expr_match = re.match(r'^\((.+)\)$', val)
        if val == '((input))':
            return ('var_assign_input', var)
        elif expr_match:
            return ('var_assign_expr', var, expr_match.group(1).strip())
        else:
            return ('var_assign_literal', var, val)
    return ('error', line)

def get_input(prompt):
    try:
        if sys.stdin.isatty():
            return input(prompt + " ")
        else:
            with open('/dev/tty', 'r') as tty:
                print(prompt, end=' ', flush=True)
                return tty.readline().rstrip('\n')
    except Exception:
        print("\nError: No interactive input possible (no terminal found). Exiting.")
        sys.exit(1)

def run_s_code(lines, functions=None, parent_vars=None, parent_last_input=None):
    variables = dict(parent_vars) if parent_vars else {}
    last_input = parent_last_input if parent_last_input is not None else ""
    idx = 0
    skip_stack = []
    functions = functions if functions is not None else {}

    def scan_functions(lines):
        func_map = {}
        idx = 0
        while idx < len(lines):
            line = lines[idx]
            parsed = parse_line(line)
            if parsed and parsed[0] == "func_def":
                funcname = parsed[1]
                fstart = idx + 1
                fend = fstart
                depth = 1
                while fend < len(lines):
                    p2 = parse_line(lines[fend])
                    if p2 and p2[0] == "func_def":
                        depth += 1
                    elif p2 and p2[0] == "end":
                        depth -= 1
                        if depth == 0:
                            break
                    fend += 1
                func_map[funcname] = (fstart, fend)
                idx = fend + 1
            else:
                idx += 1
        return func_map

    if parent_vars is None:
        functions.update(scan_functions(lines))

    while idx < len(lines):
        line = lines[idx]
        parsed = parse_line(line)
        if not parsed:
            idx += 1
            continue

        if parsed[0] == "func_def":
            funcname = parsed[1]
            fstart, fend = functions[funcname]
            idx = fend + 1
            continue

        if skip_stack:
            if parsed[0] == "if":
                skip_stack.append("if")
            elif parsed[0] == "end":
                skip_stack.pop()
            idx += 1
            continue

        try:
            if parsed[0] == 'call_func':
                fname = parsed[1]
                if fname in functions:
                    fstart, fend = functions[fname]
                    run_s_code(lines[fstart:fend], functions, variables, last_input)
                else:
                    print(f"Error: Function <{fname}> not found (Line {idx+1})")
            elif parsed[0] == 'if':
                varname, value = parsed[1], parsed[2]
                if variables.get(varname, None) == value:
                    idx += 1
                else:
                    skip_stack.append("if")
                    idx += 1
                continue
            elif parsed[0] == 'end':
                idx += 1
                continue
            elif parsed[0] == 'writeinput':
                prompt = parsed[1]
                last_input = get_input(prompt)
            elif parsed[0] == 'img':
                url = parsed[1]
                print(f"[Image: {url}]")
            elif parsed[0] == 'write_system_input':
                print(last_input)
            elif parsed[0] == 'write_var':
                var = parsed[1]
                if var in variables:
                    print(variables[var])
                else:
                    print(f"Error: Variable '{var}' not found (Line {idx+1})")
            elif parsed[0] == 'write_expr':
                expr = parsed[1]
                try:
                    result = evaluate_expression(expr, variables, last_input)
                    print(result)
                except Exception as e:
                    print(f"Error: {e} (Line {idx+1})")
            elif parsed[0] == 'write_literal':
                val = parsed[1]
                def var_sub(match):
                    v = match.group(1)
                    return str(variables.get(v, f"(Error: Var '{v}' not found)"))
                print(re.sub(r'\(([a-zA-Z_][a-zA-Z0-9_]*)\)', var_sub, val))
            elif parsed[0] == 'var_assign_input':
                var = parsed[1]
                variables[var] = last_input
            elif parsed[0] == 'var_assign_expr':
                var, expr = parsed[1], parsed[2]
                try:
                    variables[var] = evaluate_expression(expr, variables, last_input)
                except Exception as e:
                    print(f"Error assigning to '{var}': {e} (Line {idx+1})")
            elif parsed[0] == 'var_assign_literal':
                var, val = parsed[1], parsed[2]
                variables[var] = val
            elif parsed[0] == 'error':
                print(f"Error on line {idx+1}: Invalid syntax or unrecognized command: \"{parsed[1]}\"")
        except Exception as e:
            print(f"Error on line {idx+1}: {e}")
        idx += 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="S2 Language Interpreter CLI")
    parser.add_argument('file', nargs='?', help="S2 program file (.s2) to run")
    parser.add_argument('--help-s2', action='store_true', help="Show S2 language help and exit")
    args = parser.parse_args()

    if args.help_s2:
        display_help()
        sys.exit(0)

    if args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                code_lines = f.read().splitlines()
            run_s_code(code_lines)
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Enter your S2 program, finish with an empty line:")
        code_lines = []
        while True:
            try:
                line = input()
                if line.strip() == "":
                    break
                code_lines.append(line)
            except EOFError:
                break
        if code_lines:
            run_s_code(code_lines)
        else:
            print("No program entered. Exiting.")
