from lucid_types import Object, Integer, String, lucid_builtins, Boolean
from lucid_helpers import disable_warnings, exprs
from sly import Lexer, Parser
import importlib
import pathlib
import click
import sys
import os

disable_warnings()

path = os.path.dirname(os.path.abspath(__file__))


class LucidLexer(Lexer):
    def __init__(self):
        self.nesting_level = 0

    tokens = {NAME, NUMBER, STRING, EXPONENT, NEWLINE, EQ, INEQ, GE, LE}
    ignore = " \t"
    literals = {"=", "+", "-", "/", ":", "{", "}", "*", "(", ")", ",", ";", "."}

    NAME = r"[a-zA-Z_][a-zA-Z0-9_]*"
    STRING = r"\".*?\""

    EXPONENT = r"\*\*"

    EQ = r"=="
    INEQ = r"!="
    GE = r"(>=|>)"
    LE = r"(<=|<)"

    @_(r"""("[^"\\]*(\\.[^"\\]*)*"|'[^'\\]*(\\.[^'\\]*)*')""")
    def STRING(self, t):
        t.value = String(self.remove_quotes(t.value))
        return t

    @_(r"\d+")
    def NUMBER(self, t):
        t.value = Integer(t.value)
        return t

    @_(r"//.*$")
    def COMMENT(self, t):
        pass

    @_(r"\{")
    def lbrace(self, t):
        t.type = "{"
        self.nesting_level += 1
        return t

    @_(r"\}")
    def rbrace(self, t):
        t.type = "}"
        self.nesting_level -= 1
        return t

    @_(r"\n+")
    def NEWLINE(self, t):
        self.lineno = t.value.count("\n")

    def remove_quotes(self, text: String):
        if text.startswith('"') or text.startswith("'"):
            return text[1:-1]
        return text


class LucidParser(Parser):
    tokens = LucidLexer.tokens

    precedence = (
        ("left", "+", "-"),
        ("left", "*", "/"),
        ("left", "EXPONENT", "EQ"),
        ("right", "UMINUS"),
    )

    def __init__(self):
        self.env = {}

    @_("")
    def statement(self, p):
        pass

    @_("var_assign")
    def statement(self, p):
        return p.var_assign

    @_('NAME "=" expr')
    def var_assign(self, p):
        return (exprs.VAR_ASSIGN, p.NAME, p.expr)

    @_("expr")
    def statement(self, p):
        return p.expr

    @_('expr "+" expr')
    def expr(self, p):
        return (exprs.ADD, p.expr0, p.expr1)

    @_('expr "-" expr')
    def expr(self, p):
        return (exprs.SUB, p.expr0, p.expr1)

    @_('expr "*" expr')
    def expr(self, p):
        return (exprs.MUL, p.expr0, p.expr1)

    @_('expr "/" expr')
    def expr(self, p):
        return (exprs.DIV, p.expr0, p.expr1)

    @_("expr EXPONENT expr")
    def expr(self, p):
        return (exprs.EXPONENT, p.expr0, p.expr1)

    @_("expr EQ expr")
    def expr(self, p):
        return (exprs.EQUALS, p.expr0, p.expr1)

    @_("expr INEQ expr")
    def expr(self, p):
        return (exprs.NOTEQUALS, p.expr0, p.expr1)

    @_("expr GE expr")
    def expr(self, p):
        return (exprs.GREATER, p.expr0, p.expr1, p.GE)

    @_("expr LE expr")
    def expr(self, p):
        return (exprs.LESS, p.expr0, p.expr1, p.LE)

    @_('"-" expr %prec UMINUS')
    def expr(self, p):
        return p.expr

    @_("NAME")
    def expr(self, p):
        return (exprs.VAR, p.NAME)

    @_("NUMBER")
    def expr(self, p):
        return (exprs.NUM, p.NUMBER)

    @_("STRING")
    def expr(self, p):
        return (exprs.STR, p.STRING)

    for i in range(1, 50):

        @_('expr "(" expr' + ' "," expr' * i + ' ")"')
        def expr(self, p):
            args = []
            skipped = 0
            for j, expr in enumerate(p):
                if expr == "," or expr == "(" or expr == ")" or expr == "":
                    skipped += 1
                    continue
                args.append(getattr(p, f"expr{j-skipped}"))
            return (exprs.CALL, *args)

        prec = list(precedence)
        precedence = tuple(prec)

    @_('expr "(" expr ")" ')
    def expr(self, p):
        return (exprs.CALL, p.expr0, p.expr1)

    @_('expr "(" ")" ')
    def expr(self, p):
        return (exprs.CALL, p.expr)

    @_('"(" expr ")"')
    def expr(self, p):
        return (exprs.PAREN, p.expr)

    @_('expr "." expr')
    def expr(self, p):
        return (exprs.GETCHILD, p.expr0, p.expr1)

    @_("expr expr")
    def expr(self, p):
        if p.expr0[1] == "using":
            return (exprs.USING, p.expr1)


class LucidExecute:
    def __init__(self, tree, env, interpreter=False):
        self.env = env
        result = self.evaluate(tree)
        if result is not None and interpreter:
            print(result)

    def evaluate(self, node):
        if isinstance(node, Object):
            return node

        if node is None:
            return None

        match node:
            case [exprs.PROGRAM, node1, node2]:
                if node1 == None:
                    self.evaluate(node2)
                else:
                    self.evaluate(node1)
                    self.evaluate(node2)

            case [exprs.PAREN, expr]:
                return self.evaluate(expr)

            case [exprs.NUM, number]:
                return Integer(number)

            case [exprs.STR, string]:
                return String(string)

            case [exprs.ADD, num1, num2]:
                return self.evaluate(num1) + self.evaluate(num2)

            case [exprs.SUB, num1, num2]:
                return self.evaluate(num1) - self.evaluate(num2)

            case [exprs.MUL, num1, num2]:
                return self.evaluate(num1) * self.evaluate(num2)

            case [exprs.DIV, num1, num2]:
                return self.evaluate(num1) / self.evaluate(num2)

            case [exprs.EXPONENT, num1, num2]:
                return self.evaluate(num1) ** self.evaluate(num2)

            case [exprs.EQUALS, num1, num2]:
                return Boolean(self.evaluate(num1) == self.evaluate(num2))

            case [
                exprs.GETCHILD,
                *args,
            ]:  # im not even going to bother with struct matching on this
                call = False
                var1 = self.evaluate((exprs.STR, node[1][1]))
                if node[2][0] == exprs.CALL:
                    call = True
                    var2 = self.evaluate((exprs.STR, node[2][1][1]))
                else:
                    var2 = self.evaluate((exprs.STR, node[2][1]))

                var1_index = self.env[var1]

                try:
                    attribute = getattr(var1_index, var2)
                except AttributeError:
                    attribute = var1_index[var2]

                if call:
                    args = []
                    for arg in node[2][2:]:
                        args.append(self.evaluate(arg))
                    return attribute(*args)
                else:
                    return attribute

            case [exprs.USING, [exprs.GETCHILD, [_, cname1], [_, cname2]]]:
                toimport = cname1 + "." + cname2
                if toimport.startswith("std."):
                    toimport = toimport.replace("std.", "std.lcd_")
                    name = toimport.replace("std.lcd_", "")
                elif toimport.endswith(".py"):
                    name = toimport.replace(".py", "")
                    toimport = name
                self.env[name] = importlib.import_module(toimport)

            case [exprs.USING, [_, name]]:
                try:
                    file = open(f"{name}.lcd", "r")
                except FileNotFoundError:
                    file = open(path + "\\" + f"{name}.lcd", "r")
                self.env[name] = import_lucid_file(file)

            case [exprs.VAR_ASSIGN, name, var]:
                if isinstance(var, str):
                    to_assign = self.evaluate((exprs.STR, var))
                elif isinstance(var, int):
                    to_assign = self.evaluate((exprs.NUM, var))
                else:
                    to_assign = self.evaluate(var)

                self.env[name] = to_assign
                return

            case [exprs.CALL, name, args]:
                func_name = node[1][1]
                args = []
                for n in node[2:]:  # args
                    args.append(self.evaluate(n))

                # call
                result = self.env[func_name](*args)
                if result:
                    return result

            case [exprs.VAR, varname]:
                try:
                    return self.env[varname]
                except LookupError:
                    print(f'Undefined variable "{varname}"!')

            case [exprs.LESS, num1, num2, type]:
                if len(type) == 2:
                    return Boolean(self.evaluate(num1) <= self.evaluate(num2))
                else:
                    return Boolean(self.evaluate(num1) < self.evaluate(num2))

            case [exprs.GREATER, num1, num2, type]:
                if len(type) == 2:
                    return Boolean(self.evaluate(num1) >= self.evaluate(num2))
                else:
                    return Boolean(self.evaluate(num1) > self.evaluate(num2))

            case ["if", expr, statement]:
                expr_result = self.evaluate(expr)
                if expr_result:
                    self.evaluate(statement)

            case ["elif", expr, statement1, statement2]:
                expr_result = self.evaluate(expr)
                if expr_result:
                    self.evaluate(statement1)
                else:
                    self.evaluate(statement2)


def import_lucid_file(file):
    local_env = {}

    data = file.read()

    lexer = LucidLexer()
    parser = LucidParser()
    tree = parser.parse(lexer.tokenize(data))
    LucidExecute(tree, local_env)
    return local_env


def interpreter():
    lexer = LucidLexer()
    parser = LucidParser()
    print("lucid v0.0.1d")
    env = lucid_builtins

    while True:

        try:
            text = input("lucid >>> ")

        except EOFError:
            break

        except KeyboardInterrupt:
            exit()

        if text:
            tree = parser.parse(lexer.tokenize(text))
            LucidExecute(tree, env, True)


def interpret_file(filename):
    lexer = LucidLexer()
    parser = LucidParser()
    env = lucid_builtins

    try:
        filepath = filename
        file = open(filepath, "r")
    except FileNotFoundError:
        filepath = path + "\\" + filename
        file = open(filepath, "r")

    sys.path.append(filepath.replace(pathlib.PurePath(filename).name, ""))

    for line in file.readlines():
        tree = parser.parse(lexer.tokenize(line))
        LucidExecute(tree, env)


@click.command()
@click.argument("filename", required=False)
def main(filename):
    if filename:
        interpret_file(filename)
    else:
        interpreter()


if __name__ == "__main__":
    main()
