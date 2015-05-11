__author__ = 'eslamelsawy'

import time
import sys

UNIVERSAL_POS = {"adv", "noun", "num", "adp", "pron", "sconj", "propn", "det", "sym", "intj", "part", "punct", "verb", "x", "aux", "conj", "adj"}
UNIVERSAL_DEP = {"foreign", "cc", "list", "nmod:tmod", "ccomp", "remnant", "nsubjpass", "csubj", "conj", "amod", "vocative", "discourse", "neg", "csubjpass", "mark", "auxpass", "mwe", "advcl", "dislocated", "aux", "det:predet", "parataxis", "xcomp", "nsubj", "nmod:npmod", "nummod", "advmod", "punct", "compound", "compound:prt", "nmod:poss", "goeswith", "case", "cop", "conj:preconj", "dep", "appos", "det", "nmod", "dobj", "acl:relcl", "iobj", "expl", "reparandum", "acl"}
OPERATIONS = {">", "<"}

class Position:
  def __init__(self, position_string):
    splitted_position = position_string.split(u",")
    self.treeID = splitted_position[0]
    self.start = splitted_position[1]
    self.end = splitted_position[2]
    self.level = splitted_position[3]

class DependencyOperation:
  def __init__(self, operator, dependency):
    self.operator = operator
    self.dependency = dependency


def load_dict(fileName):
    result = {}
    with open(fileName, 'r') as f:
        for line in f:
            splitted_line = line.split(u"\t")
            key = splitted_line[0]
            result[key] = []
            for i in range(1, len(splitted_line)):
                if not splitted_line[i].strip() == '':
                    position = Position(splitted_line[i])
                    result[key].append(position)
    f.close()
    return result

def load_relations(fileName):
    result = {}
    with open(fileName, 'r') as f:
        for line in f:
           splitted_line = line.replace("\n", "").split(u",")
           key = splitted_line[0]+"_"+splitted_line[1]+"_"+splitted_line[2]
           result[key]= splitted_line[3]

    f.close()
    return result

def precedence(operator):
    if operator == '>':
        return 1
    elif operator == '<':
        return 1
    else:
        raise ValueError("Invalid Operation")

def perform_operation(operands_stack, operation):
    # TODO: Apply algorithm in figure 8 from this paper:http://www.researchgate.net/profile/Yuqing_Wu2/publication/3943323_Structural_joins_a_primitive_for_efficient_XML_query_patternmatching/links/0fcfd50a7adbbc3498000000.pdf
    operands_stack.pop()

def main():

    # Loading Index
    start = int(round(time.time() * 1000))
    POS_DICT = load_dict("Index/posindex.txt")
    WORD_DICT = load_dict("Index/wordindex.txt")
    RELATIONS = load_relations("Index/relations.txt")
    end = int(round(time.time() * 1000))

    print("Loading Index took %f sec"%((end-start)/1000.0))
    print("Size of Index in Memory %f MB"%((sys.getsizeof(POS_DICT)+sys.getsizeof(WORD_DICT)+sys.getsizeof(RELATIONS))/(1000*1000*1.0)))

    # Query
    query = "NOUN >nsubj VERB <dobj NOUN"

    query = query.lower()
    operands_stack = []
    operations_stack = []
    for query_token in query.split():
        if OPERATIONS.__contains__(query_token[0]): # operation
            currDepOperation = DependencyOperation(query_token[0], query_token[1:])
            while len(operations_stack) != 0 and precedence(operations_stack[-1].operator) >= precedence(currDepOperation.operator):
                perform_operation (operands_stack, operations_stack.pop())
            operations_stack.append(currDepOperation)

        else: # operand
            if (POS_DICT.__contains__(query_token)):
                operands_stack.append(POS_DICT[query_token])
            else:
                operands_stack.append(WORD_DICT[query_token])
    while len(operations_stack) != 0:
        perform_operation(operands_stack, operations_stack.pop())

# Run Main
main()