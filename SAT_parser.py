OP = {"AND": "&", "OR": "|", "NEG": "~", "IMP": "->", "EQV": "<->"}
# only the function tseitin_and_variable_map is intended for use outside of this file.
# don't give it variables that start with p.
# get formula f as a string.
# variables should be in the format of one letter and then numbers, e.g. c2, x763, etc.
# and is "&", or is "|", negation is "-", implication is "->", and equivalence is "<->".
# put "(", ")" where needed, including surrounding the formula.
# and and or can have a chain, e.g. "(x1&x2&x3)"
# doesn't keep unimportant order, e.g. "(a|b|c)" may be kept as "(c|a|b)"


class FormulaNode:

    def __init__(self, value):
        self.value = value
        self.parent = None
        self.children = []

    def add_child(self, child, placement=-1):
        child.parent = self
        if placement != -1 and self.value == OP["IMP"]:
            if placement == 1:
                self.children.append(None)
                self.children.append(child)
            else:  # placement == 0
                self.children[0] = child
        else:
            self.children.append(child)
        return self

    def is_op(self):
        return self.value in OP.values()

    def is_literal(self):
        return not self.is_op() or (self.value == OP["NEG"] and not self.children[0].is_op())

    def is_flat(self):
        for child in self.children:
            if not child.is_literal():
                return False
        return True

    def __str__(self):
        if not self.is_op():
            s = self.value
        elif self.value == OP["NEG"]:
            s = self.value + str(self.children[0])
        else:
            s = '(' + str(self.children[0])
            for i in range(1, len(self.children)):
                s += self.value + str(self.children[i])
            s += ')'
        if self.parent is None and s[0] != '(':
            s = '(' + s + ')'
        return s

    # return the set of variables that appear the formula
    def find_variables(self):
        var_set = set()
        if not self.is_op():
            var_set.add(self.value)
        else:
            for child in self.children:
                var_set = var_set.union(child.find_variables())
        return var_set


# s[0].isalpha()
def node_variable(s):
    for j in range(1, len(s)):
        if not s[j].isdigit():
            return s[j:], FormulaNode(s[:j])


# "~"
def node_unary(s):
    node = FormulaNode(s[0])
    s, child = next_node(s[1:])
    return s, node.add_child(child)


# "->" or "<->" or "&" or "|"
def node_binary(s):
    op = ""
    for operator in OP:
        if s[:len(OP[operator])] == OP[operator]:
            op = operator
            break
    node = FormulaNode(OP[op])
    s, child = next_node(s[len(OP[op]):])
    if (op == "OR" or op == "AND") and child.value == OP[op]:
        for grandchild in child.children:
            node.add_child(grandchild)
    else:
        node.add_child(child, placement=1)
    while (op == "OR" or op == "AND") and s[0] == OP[op]:
        s, child = next_node(s[len(OP[op]):])
        if child.value == OP[op]:
            for grandchild in child.children:
                node.add_child(grandchild)
        else:
            node.add_child(child)
    return s, node


# "("
def node_open_p(s):
    s, node = next_node(s[1:])
    if not s[0] == ')':
        s, new_node = next_node(s)
        node = new_node.add_child(node, placement=0)
    return s[1:], node


def next_node(s):
    if len(s) == 0:
        print("Error: called next_node() on empty string")
        return
    elif s[0].isalpha():
        return node_variable(s)
    elif s[0] == OP["NEG"]:
        return node_unary(s)
    elif s[0] == OP["AND"] or s[0] == OP["OR"] or s[0] == OP["IMP"][0] or s[0] == OP["EQV"][0]:
        return node_binary(s)
    elif s[0] == "(":
        return node_open_p(s)
    else:
        print("Error. unknown token '" + s[0] + "' in", s)


# get formula f as a string.
# variables should be in the format of one letter and then numbers, e.g. c2, x763, etc.
# and is "&", or is "|", negation is "-", implication is "->", and equivalence is "<->".
# put "(", ")" where needed, including surrounding the formula.
# and and or can have a chain, e.g. "(x1&x2&x3)"
# doesn't keep unimportant order, e.g. "(a|b|c)" is kept as "(c|a|b)"
def parse(s):
    return next_node(s)[1]


def add_and_or_children(new_children, op, node=None):
    if node is None:
        node = FormulaNode(op)
    for child in new_children:
        if child.value == node.value:
            for grandchild in child.children:
                node.add_child(grandchild)
        else:
            node.add_child(child)
    return node


def remove_imp_eqv(root):
    if root.is_literal():
        return root
    if root.value == OP["NEG"]:
        return FormulaNode(OP["NEG"]).add_child(remove_imp_eqv(root.children[0]))
    if root.value == OP["EQV"]:  # (a<->b) : ((~a|b)&(~b|a))
        a = remove_imp_eqv(root.children[0])
        b = remove_imp_eqv(root.children[1])
        left = FormulaNode(OP["OR"]).add_child(FormulaNode(OP["NEG"]).add_child(a)).add_child(b)
        right = FormulaNode(OP["OR"]).add_child(FormulaNode(OP["NEG"]).add_child(b)).add_child(a)
        return FormulaNode(OP["AND"]).add_child(left).add_child(right)
    if root.value == OP["IMP"]:  # (a->b): (~a|b)
        a = remove_imp_eqv(root.children[0])
        b = remove_imp_eqv(root.children[1])
        return FormulaNode(OP["OR"]).add_child(FormulaNode(OP["NEG"]).add_child(a)).add_child(b)
    # &, |
    new_children = [remove_imp_eqv(child) for child in root.children]
    return add_and_or_children(new_children, root.value)


def push_neg(root):
    if root.is_literal():
        return root
    if root.value == OP["NEG"]:
        root = root.children[0]
        if root.value == OP["NEG"]:
            return push_neg(root.children[0])
        op = OP["AND"]
        if root.value == OP["AND"]:
            op = OP["OR"]
        new_children = [push_neg(FormulaNode(OP["NEG"]).add_child(child))
                        for child in root.children]
        return add_and_or_children(new_children, op)
    #  &, |
    new_children = [push_neg(child) for child in root.children]
    return add_and_or_children(new_children, root.value)


# in a function without ->, <->, collapse all and's and or's to how they should be...
def collapse_and_or(root):
    if root.is_literal():
        return root
    if root.value == OP["NEG"]:
        return FormulaNode(OP["NEG"]).add_child(collapse_and_or(root.children[0]))
    #  &, |
    return add_and_or_children(root.children, root.value)


def convert_to_nnf(root):
    return collapse_and_or(push_neg(remove_imp_eqv(root)))


def flatten_and_or(root):
    def op():
        if root.value == OP["OR"]:
            return OP["AND"]
        return OP["OR"]

    if root.is_flat():
        return root
    other_children = []
    k = 0
    for i in range(len(root.children)):  # find one violation
        if root.children[i].is_literal():
            other_children.append(root.children[i])
        else:
            k = i
            break
    for i in range(k + 1, len(root.children)):  # all the others
        other_children.append(root.children[i])
    grandchildren = [flatten_and_or(child) for child in root.children[k].children]
    new_children = [flatten_and_or(add_and_or_children(other_children + [child], root.value))
                    for child in grandchildren]
    return add_and_or_children(new_children, op())


#  this function is to be used only in tseitins_transformation, when the root is and, and every
#  child is either an or or a literal. (or the root is a literal or a flat or)
def convert_to_cnf(root):
    if root.is_literal():
        return root
    new_root = FormulaNode(OP["AND"])
    for clause in root.children:
        if clause.is_flat():
            new_root.add_child(clause)
        else:
            for new_clause in flatten_and_or(clause).children:
                new_root.add_child(new_clause)
    return new_root


def cnf_nodes_to_list(root):
    if root.is_literal():
        return [[str(root)]]
    if root.value == OP["OR"]:
        return [[str(literal) for literal in root.children]]
    if root.value == OP["AND"]:
        n_list = []
        for clause in root.children:
            if clause.is_literal():
                n_list.append([str(clause)])
            else:
                n_list.append([str(literal) for literal in clause.children])
        return n_list


# don't have variables that start with p in your formula.
def tseitins_transformation(root):
    def next_var():
        i[0] += 1
        return "p" + str(i[0])

    def add_subformula(var, node):
        if node.is_literal():
            return node
        if node.value == OP["NEG"]:
            var_node = FormulaNode(var)
            add_subformula(var, node.children[0])
            return FormulaNode(OP["NEG"]).add_child(var_node)
        var_node = FormulaNode(var)
        new_node = FormulaNode(node.value)
        new_root.add_child(FormulaNode(OP["EQV"]).add_child(var_node).add_child(new_node))
        for child in node.children:
            new_node.add_child(add_subformula(next_var(), child))
        return var_node

    if root.is_literal():
        return cnf_nodes_to_list(root)
    i = [-1]
    if "p" in str(root):
        print("Error. don't have variables that start with p in your formula.")
    p0 = next_var()
    new_root = FormulaNode(OP["AND"]).add_child(FormulaNode(p0))
    add_subformula(p0, root)
    return convert_to_cnf(convert_to_nnf(new_root))


# returns the transformation result as a cnf int list,
# and mapping between the original vars and the numbers
def tseitin_and_variable_map(f):
    def switch(v):
        if v[0] == OP["NEG"]:
            return -1 * switch(v[1:])
        return var_map[v]

    f = parse(f)
    original_vars = list(f.find_variables())
    var_map = {}
    for i in range(len(original_vars)):
        var_map[original_vars[i]] = i
    f = tseitins_transformation(f)
    new_vars = list(f.find_variables())
    for i in range(len(new_vars)):
        var_map[new_vars[i]] = i + len(original_vars)
    f = cnf_nodes_to_list(f)
    for i in range(len(f)):
        for j in range(len(f[i])):
            f[i][j] = switch(f[i][j])
    original_var_map = {}
    for ov in original_vars:
        original_var_map[ov] = var_map[ov]
    return f, original_var_map


def example():
    f = "(~e|~(a->b)|~((b<->~a)|~(v3&e)))"
    print("The function is:", f)
    print("The cnf after the transformation: ")
    print(tseitins_transformation(parse(f)))
    f, m = tseitin_and_variable_map(f)
    print("As an int list:")
    print(f)
    print("With the variable map:")
    print(m)

# example()