__author__ = 'eslamelsawy'

import time
import sys
import networkx as nx
import matplotlib.pyplot as plt
import shutil
import os


UNIVERSAL_POS = {"adv", "noun", "num", "adp", "pron", "sconj", "propn", "det", "sym", "intj", "part", "punct", "verb", "x", "aux", "conj", "adj"}
UNIVERSAL_DEP = {"foreign", "cc", "list", "nmod:tmod", "ccomp", "remnant", "nsubjpass", "csubj", "conj", "amod", "vocative", "discourse", "neg", "csubjpass", "mark", "auxpass", "mwe", "advcl", "dislocated", "aux", "det:predet", "parataxis", "xcomp", "nsubj", "nmod:npmod", "nummod", "advmod", "punct", "compound", "compound:prt", "nmod:poss", "goeswith", "case", "cop", "conj:preconj", "dep", "appos", "det", "nmod", "dobj", "acl:relcl", "iobj", "expl", "reparandum", "acl"}
OPERATIONS = {">>", "<<", ">", "<"}  # sort operation in descending order of length
RIGHT_HEAD_OPERATIONS = [">>", ">"]
LEFT_HEAD_OPERATIONS = ["<<", "<"]
PARENT_CHILD_OPERATIONS = [">", "<"]
MAX_TREE_ID = -1
RELATIONS = {}


class Position:
  def __init__(self):
    self.treeID = None
    self.start = None
    self.end = None
    self.level = None

  def __str__(self):
    return "<" + self.treeID + " ," + self.start + " ," + self.end+" ," + self.level + ">"

  def __repr__(self):
    return str(self)


def position_factory(position_string):
    splitted_position = position_string.split(u",")
    position = Position()
    position.treeID = int(splitted_position[0])
    position.start = int(splitted_position[1])
    position.end = int(splitted_position[2])
    position.level = int(splitted_position[3])
    return position


class DependencyOperation:
    def __init__(self, operator_token):
        for operation in OPERATIONS:
            if operator_token.startswith(operation):
                self.operator = operation
                self.dependency = operator_token[len(operation):]
                break

    def __str__(self):
        return self.operator+"_"+self.dependency

    def __repr__(self):
        return str(self)


class MergeCandidate:
    def __init__(self, position, history_list):
        self.position = position  # of type Position
        self.history_list = history_list
        self.inherit_list = []  # list of type MergeOutput
        self.self_list = []  # list of type MergeOutput


class MergeOutput:
    def __init__(self, head, history_list = []):
        self.head = head  # of type Position
        self.history_list = history_list  # list of int representing the start positions of the matching nodes to the query


def load_dict(fileName):
    global MAX_TREE_ID
    result = {}
    with open(fileName, 'r') as f:
        for line in f:
            splitted_line = line.split(u"\t")
            key = splitted_line[0]
            result[key] = {}
            for i in range(1, len(splitted_line)):
                if not splitted_line[i].strip() == '':
                    position = position_factory(splitted_line[i])
                    if position.treeID not in result[key]:
                        result[key][position.treeID] = []
                    result[key][position.treeID].append(position)
                    MAX_TREE_ID = max(MAX_TREE_ID, position.treeID)
    f.close()
    return result

def load_tree_nodes(file_name):
    nodes = {}
    nodes_labels = {}
    tree_id = 0
    is_labels_line = False
    with open(file_name, 'r') as f:
        for line in f:
            if is_labels_line:
                nodes_labels[tree_id] = [item.replace(" ","\n") for item in line.split(u"\t")]
                tree_id += 1
            else:
                nodes[tree_id] = [int(item) for item in line.split(u"\t")]
            is_labels_line = not is_labels_line
    f.close()
    return nodes, nodes_labels

def load_tree_edges(file_name):
    edges = {}
    edges_labels = {}
    tree_id = 0
    is_labels_line = False

    with open(file_name, 'r') as f:
        for line in f:
            if line.strip() == '':
                tree_id += 1
                continue
            if is_labels_line:
                edges_labels[tree_id] = line.split(u"\t")
                tree_id += 1
            else:
                edges[tree_id] = [(int(item.split(",")[0]), int(item.split(",")[1])) for item in line.split(u"\t")]
            is_labels_line = not is_labels_line
    f.close()
    return edges, edges_labels


def load_relations(fileName):
    global RELATIONS
    RELATIONS = {}
    with open(fileName, 'r') as f:
        for line in f:
           splitted_line = line.replace("\n", "").split(u",")
           key = str(splitted_line[0]+"_"+splitted_line[1]+"_"+splitted_line[2])
           RELATIONS[key]= str(splitted_line[3])

    f.close()
    return RELATIONS

def load_sentences(file_name):
    sentences = {}
    tree_id = 0
    with open(file_name, 'r') as f:
        for line in f:
            sentences[tree_id] = ""
            counter = 0
            for token in line.split("\t"):
                if counter == 15:
                    counter = 0
                    sentences[tree_id] += "\n"+token
                else:
                    sentences[tree_id] += " "+token
                counter += 1
            tree_id += 1
    f.close()
    return sentences

def precedence(operator):  # All operations have same precedence, might change later
    return 1


def precedence_check(top_stack_operation, new_operation):
    top_stack_percedence = precedence(top_stack_operation)
    new_precedence = precedence(new_operation)

    if is_right_head_operation(top_stack_operation):  # left first when equal precedence operations
        return top_stack_percedence >= new_precedence
    else:  # left head operation, so right first when equal precedence operations
        return top_stack_percedence > new_precedence


def is_operation(query_token):
    for operation in OPERATIONS:
        if query_token.startswith(operation):
            return True
    return False


def is_pos(token):
    return UNIVERSAL_POS.__contains__(token)


def is_right_head_operation(operator):
    return RIGHT_HEAD_OPERATIONS.__contains__(operator)


def is_parent_child_operation(operator):
    return PARENT_CHILD_OPERATIONS.__contains__(operator)


def check_parent_child_relation(anc_position, des_position, operation):
    if not anc_position.level + 1 == des_position.level:
        return False
    elif not operation.dependency == "":
        relation_key = str(anc_position.treeID) + "_" + str(des_position.start) + "_" + str(anc_position.start)
        if RELATIONS.has_key(relation_key) and not RELATIONS[relation_key] == operation.dependency:
            return False
    return True


# Algorithm in figure 8 from this paper:http://www.researchgate.net/profile/Yuqing_Wu2/publication/3943323_Structural_joins_a_primitive_for_efficient_XML_query_patternmatching/links/0fcfd50a7adbbc3498000000.pdf
def merge_lists(first_list, second_list, operation):
    # create a dummy position with start=MaxInt to mark the end of the list
    dummy_position = Position()
    dummy_position.start = sys.maxint
    first_list.append(MergeOutput(dummy_position))
    second_list.append(MergeOutput(dummy_position))

    # Based on the operation, determine the ancestor and descendant lists
    ancestor_list = second_list
    descendant_list = first_list
    if is_right_head_operation(operation.operator):
        ancestor_list = first_list
        descendant_list = second_list

    # Algorithm Figure 8 in paper "Structural joins a primitive for efficient xml query pattern matching"
    merge_output_list = []
    ancestor_list_ptr = 0
    descendant_list_ptr = 0
    merge_stack = []
    while not len(merge_stack) == 0 or not ancestor_list[ancestor_list_ptr].head.start == sys.maxint or not descendant_list[descendant_list_ptr].head.start == sys.maxint:
        a_position = ancestor_list[ancestor_list_ptr].head
        d_position = descendant_list[descendant_list_ptr].head
        a_history = ancestor_list[ancestor_list_ptr].history_list
        d_history = descendant_list[descendant_list_ptr].history_list
        stack_top = merge_stack[-1].position if not len(merge_stack) == 0 else None
        if stack_top is not None and a_position.start > stack_top.end and d_position.start > stack_top.end:
            stack_top = merge_stack.pop()
            if len(merge_stack) == 0:
                merge_output_list.extend(stack_top.inherit_list)
            else:
                stack_top.self_list.extend(stack_top.inherit_list)
                merge_stack[-1].inherit_list.extend(stack_top.self_list)
        elif a_position.start < d_position.start:
            merge_stack.append(MergeCandidate(a_position, a_history))
            ancestor_list_ptr += 1
        else:
            for stack_itr in range(0, len(merge_stack)):
                stack_element = merge_stack[stack_itr]
                if is_parent_child_operation(operation.operator) and not check_parent_child_relation(stack_element.position, d_position, operation):
                    continue
                merge_history_list = list(stack_element.history_list)
                merge_history_list.extend(d_history)
                merge_history_list.append(d_position.start)
                if stack_itr == 0:  # bottom of the stack
                    merge_output_list.append(MergeOutput(stack_element.position, merge_history_list))
                else:
                    stack_element.self_list.append(MergeOutput(stack_element.position, merge_history_list))
            descendant_list_ptr += 1
    return merge_output_list


def ConvertToOutputFormat(position_list):  # return list of MergeOutput from list of Position
    merge_output_list = []
    for position in position_list:
        merge_output_list.append(MergeOutput(position))

    return merge_output_list

def draw_match (match_id, tree_id, matching_nodes, tree_nodes, tree_nodes_labels, tree_edges, tree_edges_labels, sentence):
    # print str(len(matching_nodes))+","+str(len(tree_nodes))
    # print sentence
    # print "treeid:"+str(tree_id)
    # print "TreeNodes:"+",".join(str(item) for item in tree_nodes)+"\n"
    # print "TreeEdges:"+"\t".join(str(item) for item in tree_edges)+"\n"
    # print "Matchings:"+",".join(str(item) for item in matching_nodes)+"\n"
    # print "========="

    G = nx.DiGraph()
    edge_labels_dict = {}
    node_labels_dict = {}
    for i in range(0, len(tree_nodes)):
        G.add_node(tree_nodes[i])
        node_labels_dict[tree_nodes[i]] = tree_nodes_labels[i]

    for i in range(0, len(tree_edges)):
        G.add_edge(tree_edges[i][0], tree_edges[i][1])
        edge_labels_dict[tree_edges[i]] = tree_edges_labels[i]

    # write dot file to use with graphviz
    # run "dot -Tpng test.dot >test.png"
    # nx.write_dot(G,'test.dot')

    # same layout using matplotlib with no labels
    #plt.title("Tree Number = " + str(tree_id))

    plt.title("\nSentence #" + str(tree_id)+" :"+sentence, fontsize=8)
    pos=nx.graphviz_layout(G,prog='dot')
    nx.draw(G,pos,with_labels=False,arrows=True,rankdir = "TB")
    nx.draw_networkx_nodes(G,pos,node_size=400,nodelist=tree_nodes, node_color='w',linewidths=None)
    nx.draw_networkx_nodes(G,pos,node_size=400,nodelist=matching_nodes, node_color='r')
    nx.draw_networkx_labels(G,pos, labels=node_labels_dict, font_size=6)
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels_dict, font_size=6)
    plt.savefig('Output/'+str(match_id)+'.png')
    plt.clf()

def remove_duplicates(merge_output_list):
    unique_merge_output_list = []
    unique_results = []  # list of sets
    for merge_output in merge_output_list:
        # create a set
        curr_set = set(merge_output.history_list)
        curr_set.add(merge_output.head.start)

        # check if one item is a duplicate of another in the same set
        if not len(curr_set) == len(merge_output.history_list) + 1:
            continue

        # check if duplicate with previous set
        is_duplicate = False
        for unique_result in unique_results:
            if curr_set == unique_result:
                is_duplicate = True
                break

        if not is_duplicate:
            unique_results.append(curr_set)
            unique_merge_output_list.append(merge_output)

    return unique_merge_output_list


POS_DICT = WORD_DICT = RELATIONS = TREE_NODES = TREE_NODES_LABELS =  TREE_EDGES = TREE_EDGES_LABELS = SENTENCES = SENTENCES_POS ={}

def main():
    global POS_DICT, WORD_DICT, RELATIONS, TREE_NODES, TREE_NODES_LABELS, TREE_EDGES, TREE_EDGES_LABELS, SENTENCES, SENTENCES_POS

    # Phase #1: Loading Index
    start = int(round(time.time() * 1000))
    POS_DICT = load_dict("Index/posindex.txt")
    WORD_DICT = load_dict("Index/wordindex.txt")
    load_relations("Index/relations.txt")
    TREE_NODES, TREE_NODES_LABELS = load_tree_nodes("Index/treenodes.txt")
    TREE_EDGES, TREE_EDGES_LABELS = load_tree_edges("Index/treeedges.txt")
    SENTENCES = load_sentences("Index/sentences.txt")
    end = int(round(time.time() * 1000))

    print "Phase #1: Loading Index"
    print("Number of Trees: %d"%MAX_TREE_ID)
    print("Loading Index took %f sec"%((end-start)/1000.0))
    print("Size of Index in Memory %f MB"%((sys.getsizeof(POS_DICT)+sys.getsizeof(WORD_DICT)+sys.getsizeof(RELATIONS))/(1000*1000*1.0)))
    print "\n"

    while True:
        print '======================================================================================'
        query = raw_input('Type a GFL++ query (e.g., NOUN >nsubj VERB <dobj NOUN), or hit the return key to exit:')
        if len(query) == 0:
            print 'Thanks for using the universal dependencies analyzer! Good bye!'
            break

        # Phase #2: Parse Query => Postfix Expression
        query = query.lower()
        unique_operands = set()
        postfix_query = []
        operations_stack = []
        for query_token in query.split():
            if is_operation(query_token):  # operation
                curr_operation = DependencyOperation(query_token)
                while len(operations_stack) != 0 and precedence_check(operations_stack[-1].operator, curr_operation.operator):
                    postfix_query.append(operations_stack.pop())
                operations_stack.append(curr_operation)
            else:  # operand
                postfix_query.append(query_token)
                unique_operands.add(query_token)
        while len(operations_stack) != 0:
            postfix_query.append(operations_stack.pop())

        # print "Phase #2: Parsing Query"
        print "Infix Query: "+query
        print "Postfix query: " + ", ".join(str(item) for item in postfix_query)
        # print "Unique operands: " + ", ".join(unique_operands)
        # print "\n"

        # Phase #3: Find trees which contain all operands
        start = int(round(time.time() * 1000))
        common_trees = []
        for tree_id in range(0, MAX_TREE_ID+1):
            is_common_tree = True
            for operand in unique_operands:
                if (is_pos(operand) and tree_id in POS_DICT[operand]) or (not is_pos(operand) and tree_id in WORD_DICT[operand]):
                    continue
                is_common_tree = False
            if is_common_tree:
                common_trees.append(tree_id)
        end = int(round(time.time() * 1000))

        # For Debugging
        # print "Phase #3: Finding Common Trees"
        print "Number of common trees = %d" % len(common_trees)
        print("Time taken %f ms" % (end-start))
        print "\n"

        # Phase #4: Evaluate the query for each common tree
        start = int(round(time.time() * 1000))
        matches = []
        for tree_id in common_trees:
            operands_stack = []
            for query_token in postfix_query:
                if type(query_token) is str:  # therefore query_token is operand, so push it to the stack
                    if is_pos(query_token):
                        operands_stack.append(ConvertToOutputFormat(POS_DICT[query_token][tree_id]))
                    else:
                        operands_stack.append(ConvertToOutputFormat(WORD_DICT[query_token][tree_id]))
                else:  # therefore query_toke is operation, so pop top 2 operands in the stack
                    merge_output_list = merge_lists(operands_stack.pop(), operands_stack.pop(), query_token)
                    operands_stack.append(merge_output_list)
            # operands_stack should now contain list of results
            if not len(operands_stack) == 1:
                raise ValueError("Something went wrong")
            matches.extend(remove_duplicates(operands_stack.pop()))
        end = int(round(time.time() * 1000))

        # print "Phase #4: Finding Matches"
        print ("%d matches found in %f ms"%(len(matches),(end-start)))
        # print "\n"
        print "Drawing first 10 results in Output folder..."

        # Phase 5: Drawing first 10 matches

        dir = 'Output'
        if os.path.exists(dir):
            shutil.rmtree(dir)  # cleaning output folder
        os.makedirs(dir)

        for match_id in range(0,10):
            if match_id < len(matches):
                match = matches[match_id]
                tree_id = match.head.treeID
                matching_nodes = match.history_list[:]
                matching_nodes.append(match.head.start)
                draw_match (match_id, tree_id, matching_nodes, TREE_NODES[tree_id], TREE_NODES_LABELS[tree_id], TREE_EDGES[tree_id], TREE_EDGES_LABELS[tree_id], SENTENCES[tree_id])


# Run Main
main()