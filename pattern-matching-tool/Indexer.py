__author__ = 'eslamelsawy'

import sys as sys
import time
import os

class TreeNode:
  def __init__(self):
    self.form = None
    self.pos = None
    self.parent = None
    self.relation = None
    self.start = None
    self.end = None
    self.level = None
    self.children = []

class Relation:
  def __init__(self):
    self.treeID = None
    self.pos1 = None
    self.pos2 = None
    self.relation = None

def calculate_positional_notation(node, start, level):

    node.parent = start - 1
    node.start = start
    node.level = level
    for child in node.children:
        start = calculate_positional_notation(child, start+1, level+1)
    node.end = start + 1
    return node.end

def index_tree (node, tree_id):
    pos = node.pos
    if not POS_DICT.has_key(pos):
        POS_DICT[pos] =[]
    POS_DICT[pos].append([tree_id, node.start, node.end, node.level])

    form = node.form
    if not WORD_DICT.has_key(form):
        WORD_DICT[form] = []
    WORD_DICT[form].append([tree_id, node.start, node.end, node.level])

    # add relation
    if not node.relation == 'root':
        RELATIONS.append([tree_id, node.start, node.parent, node.relation])

    for child in node.children:
        index_tree(child, tree_id)

# GLOBAL VARIABLES
POS_DICT = {}
WORD_DICT = {}
RELATIONS = []

def main():
    indexToNode = {}
    parentChildRelations = []
    root_node = None
    tree_id = 0
    with open("test-treebank") as f:
        for line in f:
            if line.strip() == '':  # new tree (sentence)
                # add parent child relations to nodes
                for relation in parentChildRelations:
                    parentId = relation[0]
                    childId = relation[1]
                    indexToNode[parentId].children.append(indexToNode[childId])

                # assign start, end, level values to each node
                calculate_positional_notation(root_node, 0, 0)

                # index the tree
                index_tree(root_node, tree_id)

                # update/reset variables for a new tree
                indexToNode = {}
                parentChildRelations = []
                root_node = None
                tree_id += 1
                continue

            # Create new Node
            splittedLine = line.lower().split(u"\t")

            node = TreeNode()
            node.form = splittedLine[1]
            node.pos = splittedLine[3]
            node.parent = splittedLine[6]
            node.relation = splittedLine[7]

            nodeId = splittedLine[0]
            parentId = splittedLine[6]
            indexToNode[nodeId] = node
            if node.relation == 'root':
                root_node = node
            else:
                parentChildRelations.append([parentId, nodeId])
    f.close()
    print_index()

def print_index():
    if not os.path.exists("Index"):
        os.makedirs("Index")

    with open('Index/relations.txt', 'w') as relationsFile:
        for relation in RELATIONS:
            relationsFile.write(','.join(str(item) for item in relation)+"\n")
    relationsFile.close()

    with open('Index/posindex.txt', 'w') as posIndexFile:
        for pos in POS_DICT.keys():
            posIndexFile.write(pos+"\t")
            positions = POS_DICT[pos]
            for position in positions:
                posIndexFile.write(','.join(str(item) for item in position)+"\t")
            posIndexFile.write("\n")
    posIndexFile.close()

    with open('Index/wordindex.txt', 'w') as wordIndexFile:
        for word in WORD_DICT.keys():
            wordIndexFile.write(word+"\t")
            positions = WORD_DICT[word]
            for position in positions:
                wordIndexFile.write(','.join(str(item) for item in position)+"\t")
            wordIndexFile.write("\n")
    wordIndexFile.close()

# Run Main
start = int(round(time.time() * 1000))
main()
end = int(round(time.time() * 1000))

print("Indexing took %f sec"%((end-start)/1000.0))
print("Size of Index in Memory %f MB"%((sys.getsizeof(POS_DICT)+sys.getsizeof(WORD_DICT)+sys.getsizeof(RELATIONS))/(1000*1000*1.0)))