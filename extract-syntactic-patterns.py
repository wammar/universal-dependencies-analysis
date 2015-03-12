import re
import time
import io
import sys
import argparse
import codecs
from collections import defaultdict
from copy import deepcopy

# parse/validate arguments
argparser = argparse.ArgumentParser()
argparser.add_argument("-i", "--treebank_root_dir", required=True)
argparser.add_argument("-o", "--output_filename", required=True)
argparser.add_argument("-m", "--max_non_sequential_pattern_size", type=int, default=3)
args = argparser.parse_args()

# languages = ['de', 'en', 'es', 'fi', 'fr', 'ga', 'hu', 'it', 'sv']
languages = ['en']


class TreeNode:
  position = None
  parent = None
  relation = None
  children = []
  def __hash__(self):
    return hash((self.position, self.parent, self.relation, tuple(self.children)))

  def __eq__(self, other):
    return (self.position, self.parent, self.relation, tuple(self.children)) == (other.position, other.parent, other.relation, tuple(other.children))

def read_conll_treebank(filename):
   f = codecs.open(filename, "r", "utf-8")
   corpus = []
   sentence = []
   for line in f:
       if line.startswith('#'):
           continue
       if line.strip() == "":
           corpus.append(sentence)
           sentence = []
           continue
       else:
           line = line.strip()
           cline = line.split(u"\t")
           if u'-' in cline[0] :
               continue
           sentence.append(cline)
   f.close()
   return corpus

def convert_absolute_positions_to_relative(root_node):
  # pattern is the root node of the pattern
  stack = [root_node]
  abs_positions = []
  root_position = root_node.position
  while len(stack) != 0:
    current_node = stack.pop()
    abs_positions.append(current_node.position)
    if len(current_node.children) != 0:
      stack.extend(current_node.children)

  abs_positions.sort()
  root_ind = abs_positions.find(root_position)
  ind_list = range(1, len(abs_positions)+1)

  ind_dict = {}
  for position in abs_positions:
    ind_dict[position] = ind_list[position] - root_ind

  while len(stack) != 0:
    current_node = stack.pop()
    current_node.position = ind_dict[current_node.position]
    if len(current_node.children) != 0:
      stack.extend(current_node.children)


def extend_pattern_up(small_pattern, parent_original_node, position_to_tree_node):
  copy_parent = TreeNode()
  copy_parent.position = parent_original_node.position
  copy_parent.pos = parent_original_node.pos

  copy_small_pattern = deepcopy(small_pattern)
  copy_small_pattern.parent = copy_parent
  copy_small_pattern.relation = position_to_tree_node[small_pattern.position].relation
  copy_parent.children = [copy_small_pattern]
  return copy_parent


def extend_pattern_down(small_pattern, child_original_node, position_to_tree_node):
  # identify the position of the parent of the child we want to add
  position_of_childs_parent = child_original_node.parent.position

  # traverse a copy of the small pattern to find that parent
  copy_of_small_pattern = deepcopy(small_pattern)
  stack = [copy_of_small_pattern]
  childs_parent = None
  while len(stack) != 0:
    current_node = stack.pop()
    if current_node.position == position_of_childs_parent:
      childs_parent = current_node
      break
    stack.extend(current_node.children)
  assert(childs_parent != None)

  # create the child and attach it to its parent
  copy_of_child = TreeNode()
  copy_of_child.parent = childs_parent
  copy_of_child.relation = child_original_node.relation
  copy_of_child.pos = child_original_node.pos
  copy_of_child.position = child_original_node.position


  # update the children's list in that parent
  child_added = False
  for child_index in xrange(len(childs_parent.children)):
    if childs_parent.children[child_index].position > copy_of_child.position:
      childs_parent.children.insert(child_index, copy_of_child)
      child_added = True
      break
  if not child_added:
    childs_parent.children.append(copy_of_child)

def extract_patterns_from_sent(conll_lines, all_patterns, language, sent_id):
  # first, create all tree nodes and set their position variable
  position_to_tree_node = [TreeNode()]
  position_to_tree_node[0].position = 0
  for i in xrange(len(conll_lines)):
    position_to_tree_node.append(TreeNode())
    position_to_tree_node[-1].position = int(conll_lines[i][0])

  # then read the conll lines and attach parents with children
  for line in conll_lines:
    position = int(line[0])
    parent_position = int(line[6])
    node = position_to_tree_node[position]
    node.parent = position_to_tree_node[parent_position]
    node.relation = line[7]
    node.pos = line[3]
    position_to_tree_node[parent_position].children.append(node)

  # ok, now we have the parse tree. then, extract patterns from it.
  size_to_patterns = []
  size_to_patterns.append(None)
  size_to_patterns.append(set())

  # patterns of size 1 (trivial)
  for position in xrange(0, len(conll_lines)+1):
    original_node = position_to_tree_node[position]
    modified_node = deepcopy(original_node)
    modified_node.children = []
    modified_node.parent = None
    modified_node.relation = None
    size_to_patterns[1].add(modified_node)

  # recurse
  for k in xrange(2, args.max_non_sequential_pattern_size):
    size_to_patterns.append(set())
    # extend each pattern of size k-1
    for small_pattern in size_to_patterns[k-1]:
      # find the parent of this pattern
      # disclaimer: when the root of the small pattern is the ROOT symbol (i.e., position = 0), its parent will be None 
      parent_original_node = position_to_tree_node[small_pattern.position].parent
      # extend the small pattern up
      if parent_original_node != None:
        size_to_patterns[k].add(extend_pattern_up(small_pattern, parent_original_node, position_to_tree_node))

      # find children positions of this pattern
      pattern_leaf_positions = []
      small_pattern_stack = [small_pattern]
      while len(small_pattern_stack) != 0:
        current_node = small_pattern_stack.pop()
        if len(current_node.children) == 0:
          pattern_leaf_positions.append(current_node.position)
        else:
          small_pattern_stack.extend(current_node.children)
      # extend the small pattern down
      for child_position in pattern_leaf_positions:
        child_original_node = position_to_tree_node[child_position]
        size_to_patterns[k].add(extend_pattern_down(small_pattern, child_original_node, position_to_tree_node))

  # replace absolute positions with relative positions then add the patterns to all_patterns  
  for k in size_to_patterns.keys():
    for pattern in size_to_patterns[k]:
      convert_absolute_positions_to_relative(pattern)
      if pattern not in all_patterns: all_patterns[pattern] = {}
      if language not in all_patterns[pattern]: all_patterns[pattern][language] = []
      all_patterns[pattern][language].append(sent_id)

def extract_all_patterns():
  # initialize the main data structure that holds all patterns
  all_patterns = {}
  for language in languages:
    treebank_filename = '{}/{}/{}-ud-train.conllu'.format(args.treebank_root_dir, language, language)
    treebank = read_conll_treebank(treebank_filename)
    for sent_id in xrange(len(treebank)):
      sent = treebank[sent_id]
      extract_patterns_from_sent(sent, all_patterns, language, sent_id)
      # test one sentence to see if it is correct
      break

if __name__ == '__main__':
  sys.stdout = codecs.getwriter('utf-8')(sys.stdout)
  sys.stderr = codecs.getwriter('utf-8')(sys.stderr)

  extract_all_patterns()
