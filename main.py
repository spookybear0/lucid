from sly import Lexer, Parser
import importlib
from lucid_types import Object, Integer, String, lucid_builtins, true, false, Boolean
import os
import click

path = os.path.dirname(os.path.abspath(__file__))

class BasicLexer(Lexer): 
    tokens = { NAME, NUMBER, STRING, EXPONENT, EQUALS, TRUEDIV } 
    ignore = "\t "
    literals = {"=", "+", "-", "/", "//", ":",
                "*", "(", ")", ",", ";", "."} 
  
    NAME = r"[a-zA-Z_][a-zA-Z0-9_]*"
    STRING = r"\".*?\""
    
    EXPONENT = r'\*\*'
    TRUEDIV = r'\/\/'
    EQUALS = r'=='
    
    @_(r'''("[^"\\]*(\\.[^"\\]*)*"|'[^'\\]*(\\.[^'\\]*)*')''')
    def STRING(self, t):
        t.value = String(self.remove_quotes(t.value))
        return t
  
    @_(r"\d+") 
    def NUMBER(self, t): 
        t.value = Integer(t.value)  
        return t 
  
    @_(r"//.*") 
    def COMMENT(self, t): 
        pass
  
    @_(r"\n+") 
    def newline(self, t): 
        self.lineno = t.value.count("\n")
        
    def remove_quotes(self, text: String):
        if text.startswith('\"') or text.startswith('\''):
            return text[1:-1]
        return text


class BasicParser(Parser): 
    tokens = BasicLexer.tokens 
  
    precedence = ( 
        ("left", "+", "-"), 
        ("left", "*", "/"), 
        ("right", "UMINUS"), 
    ) 
  
    def __init__(self): 
        self.env = { } 
  
    @_("") 
    def statement(self, p): 
        pass
  
    @_("var_assign") 
    def statement(self, p): 
        return p.var_assign 
  
    @_('NAME "=" expr') 
    def var_assign(self, p): 
        return ("var_assign", p.NAME, p.expr) 
  
    @_('NAME "=" STRING') 
    def var_assign(self, p): 
        return ("var_assign", p.NAME, p.STRING) 
  
    @_("expr") 
    def statement(self, p): 
        return (p.expr) 
  
    @_('expr "+" expr') 
    def expr(self, p): 
        return ("add", p.expr0, p.expr1) 
  
    @_('expr "-" expr') 
    def expr(self, p): 
        return ("sub", p.expr0, p.expr1) 
  
    @_('expr "*" expr') 
    def expr(self, p): 
        return ("mul", p.expr0, p.expr1) 
  
    @_('expr "/" expr') 
    def expr(self, p): 
        return ("div", p.expr0, p.expr1) 
    
    @_('expr EXPONENT expr') 
    def expr(self, p): 
        return ("exponent", p.expr0, p.expr1) 
    
    @_('expr TRUEDIV expr') 
    def expr(self, p): 
        return ("truediv", p.expr0, p.expr1) 
    
    @_('expr EQUALS expr') 
    def expr(self, p): 
        return ("equals", p.expr0, p.expr1) 
  
    @_('"-" expr %prec UMINUS') 
    def expr(self, p): 
        return p.expr 
  
    @_("NAME") 
    def expr(self, p): 
        return ("var", p.NAME) 
  
    @_("NUMBER") 
    def expr(self, p): 
        return ("num", p.NUMBER)
    
    @_("STRING") 
    def expr(self, p): 
        return ("str", p.STRING)
    
    for i in range(1, 50):
        @_('expr "(" expr' + ' "," expr' * i + ' ")"')
        def expr(self, p):
            args = []
            skipped = 0
            for j, expr in enumerate(p):
                if expr == ',' or expr == '(' or expr == ')' or expr == "":
                    skipped += 1
                    continue
                args.append(getattr(p, f"expr{j-skipped}"))
            return ("call", *args)
    
    @_('expr "(" expr ")" ')
    def expr(self, p):
        return ("call", p.expr0, p.expr1)

    @_('expr "(" ")" ')
    def expr(self, p):
        return ("call", p.expr)
    
    @_('"(" expr ")"')
    def expr(self, p):
        return ("paren", p.expr)
    
    @_('expr "." expr')
    def expr(self, p):
        return ("getchild", p.expr0, p.expr1)
    
    @_('expr expr')
    def expr(self, p):
        if p.expr0[1] == "using":
            return ("import", p.expr1)

class BasicExecute: 
    
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
            case ["program", node1, node2]: 
                if node1 == None: 
                    self.evaluate(node2) 
                else: 
                    self.evaluate(node1) 
                    self.evaluate(node2) 
                    
            case ["paren", expr]:
                return self.evaluate(expr)
    
            case ["num", number]:
                return Integer(number)
    
            case ["str", string]: 
                return String(string)
    
            case ["add", num1, num2]:
                return self.evaluate(num1) + self.evaluate(num2)
            
            case ["sub", num1, num2]: 
                return self.evaluate(num1) - self.evaluate(num2)
            
            case ["mul", num1, num2]: 
                return self.evaluate(num1) * self.evaluate(num2)
            
            case ["div", num1, num2]:
                return self.evaluate(num1) / self.evaluate(num2)
            
            case ["exponent", num1, num2]:
                return self.evaluate(num1) ** self.evaluate(num2)
            
            case ["truediv", num1, num2]:
                return self.evaluate(num1) // self.evaluate(num2)
            
            case ["equals", num1, num2]:
                return Boolean(self.evaluate(num1) == self.evaluate(num2))
            
            case ["getchild", *args]: # im not even going to bother with struct matching on this
                call = False
                var1 = self.evaluate(("str", node[1][1]))
                if node[2][0] == "call":
                    call = True
                    var2 = self.evaluate(("str", node[2][1][1]))
                else:
                    var2 = self.evaluate(("str", node[2][1]))
                
                attribute = getattr(self.env[var1], var2)
                
                if call:
                    args = []
                    for arg in node[2][2:]:
                        args.append(self.evaluate(arg))
                    return attribute(*args)
                else:
                    return attribute
                
            case ["import", ["getchild", [_, cname1], [_, cname2]]]:
                toimport = cname1 + "." + cname2
                if toimport.startswith("std."):
                    toimport = toimport.replace("std.", "std.lcd_")
                    name = toimport.replace("std.lcd_", "")
                self.env[name] = importlib.import_module(toimport)
                
            case ["import", [_, name]]:
                return NotImplementedError("Importing a single module is not supported yet")
                # should import only .lcd files
                #self.env[name] = importlib.import_module(name)
    
            case ["var_assign", name, var]:
                if isinstance(var, str):
                    to_assign = self.evaluate(("str", var))
                elif isinstance(var, int):
                    to_assign = self.evaluate(("num", var))
                else:
                    to_assign = self.evaluate(var)
                    
                self.env[name] = to_assign
                return
            
            case ["call", name, args]:
                func_name = node[1][1]
                args = []
                for n in node[2:]: # args
                    args.append(self.evaluate(n))
                    
                # call
                result = self.env[func_name](*args)
                if result:
                    return result
    
            case ["var", varname]:
                try:
                    return self.env[varname] 
                except LookupError: 
                    print(f"Undefined variable \"{varname}\"!") 

def interpreter():
    lexer = BasicLexer()
    parser = BasicParser()
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
            BasicExecute(tree, env, True)
            
def interpret_file(filename):
    lexer = BasicLexer() 
    parser = BasicParser()
    env = lucid_builtins
    
    try:
        file = open(filename, "r")
    except FileNotFoundError:
        file = open(path + "\\" + filename, "r")
    
    for line in file.readlines():
        tree = parser.parse(lexer.tokenize(line))
        BasicExecute(tree, env)

@click.command()
@click.argument("filename", required=False)
def main(filename):
    if filename:
        interpret_file(filename)
    else:
        interpreter()


if __name__ == "__main__":
    main()