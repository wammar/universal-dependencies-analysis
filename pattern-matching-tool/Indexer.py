__author__ = 'eslamelsawy'

import sys as sys
import time
import os
import codecs

class TreeNode:
  def __init__(self):
    self.form = None
    self.pos = None
    self.parent = None
    self.relation = None
    self.start = None
    self.end = None
    self.level = None
    self.sentence_pos = None
    self.children = []

class Relation:
  def __init__(self):
    self.treeID = None
    self.pos1 = None
    self.pos2 = None
    self.relation = None

def calculate_positional_notation(node, start, level, parent_start_id):

    node.parent = parent_start_id
    node.start = start
    node.level = level
    for child in node.children:
        start = calculate_positional_notation(child, start+1, level+1, node.start)
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

    # Next structures are used for drawing trees
    if not TREE_NODES.has_key(tree_id):
        TREE_NODES[tree_id] = []
        TREE_NODES_LABELS[tree_id] = []
    TREE_NODES[tree_id].append(node.start)
    TREE_NODES_LABELS[tree_id].append(node.form+" "+node.pos)

    if not TREE_EDGES.has_key(tree_id):
        TREE_EDGES[tree_id] = []
        TREE_EDGES_LABELS[tree_id] = []
    if not node.relation == 'root':
        TREE_EDGES[tree_id].append(str(node.start)+","+str(node.parent))
        TREE_EDGES_LABELS[tree_id].append(str(node.relation))

    if not SENTENCES_POS.has_key(tree_id):
        SENTENCES_POS[tree_id] = []
    SENTENCES_POS[tree_id].append(str(node.sentence_pos))

    for child in node.children:
        index_tree(child, tree_id)

# GLOBAL VARIABLES
POS_DICT = {}
WORD_DICT = {}
RELATIONS = []

TREE_NODES = {}
TREE_NODES_LABELS = {}
TREE_EDGES = {}
TREE_EDGES_LABELS = {}
SENTENCES = {}
SENTENCES_POS = {}
LANGUAGES = ["English", "French", "Spanish", "German"]
LANGUAGES_Code = {"English": "en", "French": "fr", "Spanish":"es", "German":"de"}

def reset_data_structures():
    global POS_DICT, WORD_DICT, RELATIONS, TREE_NODES, TREE_NODES_LABELS, TREE_EDGES, TREE_EDGES_LABELS, SENTENCES, SENTENCES_POS
    POS_DICT = {}
    WORD_DICT = {}
    TREE_NODES = {}
    TREE_NODES_LABELS = {}
    TREE_EDGES = {}
    TREE_EDGES_LABELS = {}
    SENTENCES = {}
    SENTENCES_POS = {}
    RELATIONS = []

def main():
    for lang in LANGUAGES:
        reset_data_structures()
        indexToNode = {}
        parentChildRelations = []
        root_node = None
        tree_id = 0
        sentence_pos = 0
        print lang
        with codecs.open("treebanks/" + lang + "/" + LANGUAGES_Code[lang] + "-ud-train.conllu", encoding='utf-8') as f:
            for line in f:
                if line.strip() == '':  # new tree (sentence)
                    # add parent child relations to nodes
                    for relation in parentChildRelations:
                        parentId = relation[0]
                        childId = relation[1]
                        indexToNode[parentId].children.append(indexToNode[childId])

                    # assign start, end, level values to each node
                    calculate_positional_notation(root_node, 0, 0, -1)

                    # index the tree
                    index_tree(root_node, tree_id)

                    # update/reset variables for a new tree
                    indexToNode = {}
                    parentChildRelations = []
                    root_node = None
                    tree_id += 1
                    sentence_pos = 0
                    continue

                # Create new Node
                splittedLine = line.lower().split(u"\t")

                node = TreeNode()
                node.form = splittedLine[1]
                node.pos = splittedLine[3]
                node.parent = splittedLine[6]
                node.relation = splittedLine[7]
                node.sentence_pos = sentence_pos

                nodeId = splittedLine[0]
                if u'-' in nodeId:
                    continue
                parentId = splittedLine[6]
                indexToNode[nodeId] = node
                if node.relation == 'root':
                    root_node = node
                else:
                    parentChildRelations.append([parentId, nodeId])

                if not SENTENCES.has_key(tree_id):
                    SENTENCES[tree_id]=[]
                SENTENCES[tree_id].append(node.form)
                sentence_pos += 1
        f.close()
        print_index(lang)

def print_index(lang):
    if not os.path.exists("Index"):
        os.makedirs("Index")

    if not os.path.exists("Index/" + lang):
        os.makedirs("Index/" + lang)

    relative_path = "Index/" + lang


    with codecs.open(relative_path + '/relations.txt', encoding='utf-8', mode='w+') as relationsFile:
        for relation in RELATIONS:
            relationsFile.write(','.join(str(item) for item in relation)+"\n")
    relationsFile.close()


    with codecs.open(relative_path + '/posindex.txt', encoding='utf-8', mode='w+') as posIndexFile:
        for pos in POS_DICT.keys():
            posIndexFile.write(pos+"\t")
            positions = POS_DICT[pos]
            for position in positions:
                posIndexFile.write(','.join(str(item) for item in position)+"\t")
            posIndexFile.write("\n")
    posIndexFile.close()


    with codecs.open(relative_path + '/wordindex.txt', encoding='utf-8', mode='w+') as wordIndexFile:
        for word in WORD_DICT.keys():
            wordIndexFile.write(word+"\t")
            positions = WORD_DICT[word]
            for position in positions:
                wordIndexFile.write(','.join(str(item) for item in position)+"\t")
            wordIndexFile.write("\n")
    wordIndexFile.close()


    with codecs.open(relative_path + '/treenodes.txt', encoding='utf-8', mode='w+') as tree_nodes_file:
        tree_ids = TREE_NODES.keys()
        tree_ids.sort()
        for tree_id in tree_ids:
            nodes = TREE_NODES[tree_id]
            nodes_labels = TREE_NODES_LABELS[tree_id]
            tree_nodes_file.write('\t'.join(str(node) for node in nodes))
            tree_nodes_file.write("\n")
            tree_nodes_file.write('\t'.join(node_label for node_label in nodes_labels))
            tree_nodes_file.write("\n")
    tree_nodes_file.close()


    with codecs.open(relative_path + '/treeedges.txt', encoding='utf-8', mode='w+') as tree_edges_file:
        tree_ids = TREE_EDGES.keys()
        tree_ids.sort()
        for tree_id in tree_ids:
            edges = TREE_EDGES[tree_id]
            edges_labels = TREE_EDGES_LABELS[tree_id]
            if len(edges_labels) == 0:
                tree_edges_file.write("\n")
                continue
            tree_edges_file.write('\t'.join(str(edge) for edge in edges))
            tree_edges_file.write("\n")
            tree_edges_file.write('\t'.join(str(edge_label) for edge_label in edges_labels))
            tree_edges_file.write("\n")
    tree_edges_file.close()

    with codecs.open(relative_path + '/sentences.txt', encoding='utf-8', mode='w+') as sentences_file:
        tree_ids = SENTENCES.keys()
        tree_ids.sort()
        for tree_id in tree_ids:
            sentences_file.write('\t'.join(SENTENCES[tree_id]))
            sentences_file.write("\n")
    sentences_file.close()


    with codecs.open(relative_path + '/sentencespos.txt', encoding='utf-8', mode='w+') as sentencespos_file:
        tree_ids = SENTENCES_POS.keys()
        tree_ids.sort()
        for tree_id in tree_ids:
            sentencespos_file.write('\t'.join(SENTENCES_POS[tree_id]))
            sentencespos_file.write("\n")
    sentencespos_file.close()

# Run Main
start = int(round(time.time() * 1000))
main()
end = int(round(time.time() * 1000))

print("Indexing took %f sec"%((end-start)/1000.0))