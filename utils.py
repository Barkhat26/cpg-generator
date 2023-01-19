from antlr4 import *
from typing import List
from hashlib import md5

from antlr4.tree.Tree import TerminalNodeImpl

from db import Database


def md5sum(s: str):
    return md5(s.encode()).hexdigest()

class Stack:
    def __init__(self):
        self.items = []

    def push(self, item):
        self.items.append(item)

    def pop(self):
        return self.items.pop()

    def peek(self):
        return self.items[-1]

    def isEmpty(self):
        return len(self.items) == 0

    def clear(self):
        self.items.clear()


class Queue:
    def __init__(self):
        self.items = []
        self.current = -1

    def push(self, item):
        self.items.insert(0, item)

    def pop(self):
        return self.items.pop()

    def peek(self):
        return self.items[-1]

    def size(self):
        return len(self.items)

    def isEmpty(self):
        return len(self.items) == 0

    def clear(self):
        self.items.clear()

    def __iter__(self):
        self.current = len(self.items) - 1
        return self

    def __next__(self):
        if self.current < 0:
            raise StopIteration
        el = self.items[self.current]
        self.current -= 1
        return el








def getOriginalCodeText(ctx: ParserRuleContext):
    start = ctx.start.start
    stop = ctx.stop.stop
    return ctx.start.getInputStream().getText(start, stop)


def isUsableExpression(expr: str) -> bool:
    # must not be a literal or of type 'class'.
    if expr.startswith("$"):
        return False
    # must not be a method-call or parenthesized expression
    if expr.endswith(")"):
        return False
    # must not be an array-indexing expression
    if expr.endswith("]"):
        return False
    # must not be post unary operation expression
    if expr.endswith("++") or expr.endswith("--"):
        return False
    # must not be a pre unary operation expression
    if expr.startswith("+") or expr.startswith("-") or expr.startswith("!") or expr.startswith("~"):
        return False
    # must not be an array initialization expression
    if expr.endswith("}"):
        return False
    # must not be an explicit generic invocation expression
    if expr.startswith("<"):
        return False

    return True


def getIdByCtx(ctx):
    if isinstance(ctx, TerminalNodeImpl):
        return md5sum(ctx.__class__.__name__ + str(ctx.symbol.start) + str(ctx.symbol.stop))
    else:
        return md5sum(ctx.__class__.__name__ + str(ctx.start.start) + str(ctx.stop.stop))


def escapeForHtml(code):
    return code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def getParExpression(code: str) -> str:
    if code.startswith("if"):
        return code[4:-1]
    if code.startswith("for"):
        return code[5:-1]
    if code.startswith("while"):
        return code[7:-1]


# Вынесенный метод из MethodInfo. Нужен для того, чтобы не вызывать findDefInfo
def doesMethodStateDef(name: str):
    prefixes = ["set", "put", "add", "insert", "push", "append"]
    for pre in prefixes:
        if name.lower().startswith(pre):
            return True

    return False

def nodeContainsCall(node):
    from db import Database
    from graphs.ast.ASNode import ASNodeKind
    astNode = None
    currentAST = None
    for AST in Database().getAllASTs().values():
        astNode = AST.getNodeByID(node.sharedId)
        currentAST = AST
        break

    if astNode is None:
        return False

    queue = Queue()
    queue.push(astNode)

    containsCall = False
    while not queue.isEmpty():
        current = queue.pop()

        if current.kind == ASNodeKind.CALL:
            containsCall = current
            break

        for on in currentAST.outNodes(current):
            queue.push(on)

    return containsCall

def getCallName(node):
    from db import Database
    from graphs.ast.ASNode import ASNodeKind
    astNode = None
    currentAST = None
    for AST in Database().getAllASTs().values():
        astNode = AST.getNodeByID(node.sharedId)
        currentAST = AST
        break
    if astNode is None:
        return None
    queue = Queue()
    queue.push(astNode)

    callNode = None
    while not queue.isEmpty():
        current = queue.pop()

        if current.kind == ASNodeKind.CALL:
            callNode = current
            break

        for on in currentAST.outNodes(current):
            queue.push(on)

    for on in currentAST.outNodes(callNode):
        if on.kind == ASNodeKind.NAME:
            return on.getCode()

def getCallArgs(node, ast):
    from graphs.ast.ASNode import ASNodeKind
    astNode = ast.getNodeByID(node.sharedId)
    queue = Queue()
    queue.push(astNode)

    callNode = None
    while not queue.isEmpty():
        current = queue.pop()

        if current.kind == ASNodeKind.CALL:
            callNode = True
            break

        for on in ast.outNodes(current):
            queue.push(on)

    for on in ast.outNodes(callNode):
        if on.kind == ASNodeKind.PARAMS:
            pass


def nodeContainsReturn(node):
    from db import Database
    from graphs.ast.ASNode import ASNodeKind
    astNode = None

    for AST in Database().getAllASTs().values():
        astNode = AST.getNodeByID(node.sharedId)
        break

    if astNode is None:
        return False

    if astNode.kind == ASNodeKind.RETURN:
        return True

    return False


def getDataFlowParent(dfg, nodeCtx, ast):
    current = ast.getNodeByCtx(nodeCtx)
    while True:
        if len(ast.inEdges[current.Id]) == 0:
            break

        # AST is not a multigraph, therefore self.ast.inEdges[current] set length is always 1 or 0 (root)
        parent = list(ast.inEdges[current.Id])[0].source
        if dfg.getNodeByID(parent.sharedId):
            return dfg.getNodeByID(parent.sharedId)
        current = parent

    return None

def isOperator(x):
    if x in ['+', '-', '/', '*']:
        return True
    else:
        return False

def preToInfix(pre_exp_list):
    s = Stack()
    for el in pre_exp_list[::-1]:
        if isOperator(el):
            op1 = s.pop()
            op2 = s.pop()
            temp = "(" + op1 + el + op2 + ")"
            s.push(temp)
        else:
            s.push(el)
    return s.peek()


def hasSuperClass(childJavaClassName, superJavaClassName, db: Database) -> bool:
    current = childJavaClassName
    while True:
        jc = db.getJavaClass(current)
        if jc.extends is None:
            break

        if jc.extends == superJavaClassName:
            return True

        current = jc.package + "." + jc.extends

    return False

def findCallers(methodQN: str) -> List[str]:
    db = Database()
    search = methodQN.split(".")[-1]

    callers = []
    for method in db.getCallGraphMethods():
        if search in db.getCallees(method):
            callers.append(method)
    return callers



