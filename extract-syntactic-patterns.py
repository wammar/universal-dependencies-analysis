import re
import time
import io
import sys
import argparse
from collections import defaultdict

# parse/validate arguments
argparser = argparse.ArgumentParser()
argparser.add_argument("-i", "--treebank_root_dir", required=True)
argparser.add_argument("-o", "--output_filename", required=True)
argparser.add_argument("-m", "--max_non_sequential_pattern_size", type=int, default=3)
args = argparser.parse_args()

languages = ['de', 'en', 'es', 'fi', 'fr', 'ga', 'hu', 'it', 'sv']

class TreeNode:
  position = None
  parent = None
  relation = None
  children = []
  def __hash__(self):
    # hash me
    pass
  def __eq__(self, other):
    #return (self.name, self.location) == (other.name, other.location)
    pass

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
           if cline[0].contains('-'):
               continue
           sentence.append(cline)
   f.close()
   return corpus

def convert_absolute_positions_to_relative(pattern):
  # lingpeng's simple algorithm
  pass

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
    node.parent = postion_to_tree[parent_position]
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
    modified_node = original_node.deepcopy()
    modified_node.children = []
    modified_node.parent = None
    size_to_patterns[1].add(modified_node)

  # recurse
  for k in xrange(2, args.max_pattern_size):
    # extend each pattern of size k-1
    for small_pattern in size_to_patterns[k-1]:
      # find the parent of this pattern
      # disclaimer: when the root of the small pattern is the ROOT symbol (i.e., position = 0), its parent will be None 
      parent_original_node = position_to_tree_node[small_pattern.position].parent
      # extend the small pattern up
      size_to_patterns[k].add(extend_pattern_up(small_pattern, parent_original_node))

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
        size_to_patterns[k].add(extend_pattern_down(small_pattern, child_original_node))

  # replace absolute positions with relative positions then add the patterns to all_patterns  
  for k in size_to_patterns.keys():
    for pattern in size_to_patterns[k]:
      convert_absolute_positions_to_relative(pattern)
      if pattern not in all_patterns: all_patterns[pattern] = {}
      if language not in all_patterns[pattern]: all_patterns[pattern][language] = []
      all_patterns[pattern][language].append(sent_id)

def extract_all_patterns:
  # initialize the main data structure that holds all patterns
  all_patterns = {}
  for language in languages:
    treebank_filename = '{}/{}/{}-ud-train.conllu'.format(args.treebank_root_dir, language, language)
    treebank = read_conll_treebank(treebank_filename)
    for sent_id in xrange(len(treebank)):
      sent = treebank[sent_id]
      extract_patterns_from_sent(sent, all_patterns, language, sent_id)

if __name__ == '__main__':
  sys.stdout = codecs.getwriter('utf-8')(sys.stdout)
  sys.stderr = codecs.getwriter('utf-8')(sys.stderr)
