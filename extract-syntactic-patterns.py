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
argparser.add_argument("-m", "--max_non_sequential_pattern_size", type=int, default=4)
args = argparser.parse_args()

# languages = ['de', 'en', 'es', 'fi', 'fr', 'ga', 'hu', 'it', 'sv']
languages = ['en', 'fr']

def print_ind(node, ind):
  s1 = ""
  for i in xrange(ind): s1 += '  '
  s1 +=  u'position:{},pos:{},parent:{},relation:{}'.format(node.position, node.pos, node.parent.position if node.parent else "None", node.relation)
  s1 += ",children:\n" if node.children else "\n"
  for c in node.children:
    s1 += print_ind(c, ind+1)
  return s1

class TreeNode:
  def __init__(self):
    self.position = None
    self.pos = None
    self.parent = None
    self.relation = None
    self.children = []

  def __hash__(self):
    result = hash((self.position, self.pos, self.parent.position if self.parent else -1, self.relation))
    for c in self.children:
      result += hash(c)
    return result

  def __eq__(self, other):
    if type(self) != type(other): return False
    if type(self) == type(None): return True

    result = (self.position, self.pos, self.parent.position if self.parent else -1, self.relation) == (other.position, other.pos, other.parent.position if other.parent else -1, other.relation)
    if not result: return result
    if len(self.children) != len(other.children): return False
    for i in xrange(len(self.children)):
      result = result and (self.children[i] == other.children[i])
      if not result: return result
    return result

  def __str__(self):
    s1 = "START\n"
    s1 += print_ind(self,0)
    return s1

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

def read_conll_treebanks():
  treebanks = {}
  for language in languages:
    treebank_filename = '{}/{}/{}-ud-train.conllu'.format(args.treebank_root_dir, language, language)
    treebanks[language] = read_conll_treebank(treebank_filename)
  return treebanks

# insitu conversion.
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
  root_ind = abs_positions.index(root_position)
  # ind_list = range(1, len(abs_positions)+1)

  ind_dict = {}
  for i in xrange(len(abs_positions)):
    position = abs_positions[i]
    ind_dict[position] = i - root_ind

  stack = [root_node]
  while len(stack) != 0:
    current_node = stack.pop()
    current_node.position = ind_dict[current_node.position]
    #print current_node.position, ind_dict[current_node.position]
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
  if child_original_node.parent == None:
    print "parent is none"
    exit(1)
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
  return copy_of_small_pattern

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
  for position in xrange(1, len(conll_lines)+1):
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
        things_to_add = extend_pattern_up(small_pattern, parent_original_node, position_to_tree_node)
        size_to_patterns[k].add(things_to_add)
        
      # find children positions of this pattern
      pattern_direct_children_positions = set()
      pattern_node_positions = set()
      small_pattern_stack = [small_pattern]
      while len(small_pattern_stack) != 0:
        current_node = small_pattern_stack.pop()
        if len(current_node.children) != 0:
          small_pattern_stack.extend(current_node.children)
        for c in position_to_tree_node[current_node.position].children:
          pattern_direct_children_positions.add(c.position)
        pattern_node_positions.add(current_node.position)

      # extend the small pattern down
      for child_position in pattern_direct_children_positions:
        if child_position in pattern_node_positions: continue
        child_original_node = position_to_tree_node[child_position]
        size_to_patterns[k].add(extend_pattern_down(small_pattern, child_original_node, position_to_tree_node))

  # replace absolute positions with relative positions then add the patterns to all_patterns  
  for k in xrange(1,len(size_to_patterns)):
    for pattern in size_to_patterns[k]:
      convert_absolute_positions_to_relative(pattern)
      if pattern not in all_patterns: all_patterns[pattern] = {}
      if language not in all_patterns[pattern]: all_patterns[pattern][language] = []
      all_patterns[pattern][language].append(sent_id)

def extract_all_patterns(treebanks):
  # initialize the main data structure that holds all patterns
  all_patterns = {}
  for language in treebanks.keys():
    treebank = treebanks[language]

    for sent_id in xrange(len(treebank)):
      sent = treebank[sent_id]
      #print_sentence(sent, sys.stdout)
      extract_patterns_from_sent(sent, all_patterns, language, sent_id)

  return all_patterns

def print_all_patterns(treebanks, all_patterns):
  print 'extracted patterns are:'
  for pattern in all_patterns:
    print pattern
    print 'instantiated in', len(all_patterns[pattern]), 'languages.'
    for lang in all_patterns[pattern].keys():
      print '  instantiations in "{}":'.format(lang)
      for sent_id in all_patterns[pattern][lang]:
        print '    sent_id:', sent_id
        #sentence = treebanks[lang][sent_id]
        #print_sentence(sentence, sys.stdout)

  return all_patterns

def print_sentence(sentence, outputf):
  for line in sentence:
    s = u""
    for field in line:
      s += field + u"\t"
    s = s.strip()
    outputf.write(s+u"\n")
  outputf.write(u"\n")
  return

not_nested_brackets = re.compile('\([^()]+\)')
def parser_gfl_query(query):
  treelets = {}
  while (True):
    match = not_nested_brackets.search(query)
    if !match: break
    bracketless_span = query[match.start()+1:match.end()-1]
    treelet = parse_gfl_query_no_brackets(bracketless_span, treelets)
    treelet_index = len(treelets)
    treelets[treelet_index] = treelet
    query = query[:match.start()] + ' #' + treelet_index + ' ' + query[match.end():]

  # after processing all brackets
  root_node = parse_gfl_query_no_brackets(query, treelets)

  # convert absolute positions to relative positions
  convert_absolute_positions_to_relative(root_node)
  return root_node



def parse_gfl_query_no_brackets(query, treelets):
  query_parts = query.split()

  # create isolated tree nodes and set their 
  # absolute position and part-of-speech properties 
  token_nodes = []
  part_index_to_node = []
  for part_index in xrange(len(query_parts)):
    if query_parts[part_index][0] == '#':
      token_nodes.append(treelets[int(query_parts[part_index][1:])])
    else if query_parts[part_index][0] not in ['<', '>']:
      token_nodes.append(TreeNode())
      token_nodes[-1].position = len(token_nodes)
      token_nodes[-1].pos = query_parts[part_index]
      part_index_to_node.append(token_nodes[-1])
    else:
      part_index_to_node.append(None)
  
  # process each arc
  for part_index in xrange(len(query_parts)):
    if query_parts[part_index][0] in ['<', '>']:
      # bad query
      if part_index == 0 or part_index == len(query_parts)-1 or \
            part_index_to_node[part_index-1] == None or \
            part_index_to_node[part_index+1] == None:
        print 'This part "{}" of the GFL++ query must appear between two parts of speech.'.format(query_parts[part_index])
        return None

      # extract information on this arc
      child_part_index = part_index-1 if query_parts[part_index][0] == '>' else part_index+1
      parent_part_index = part_index+1 if query_parts[part_index][0] == '>' else part_index-1
      relation = query_parts[part_index][1:]

      # link nodes based on this arc
      part_index_to_node[child_part_index].relation = relation
      part_index_to_node[child_part_index].parent = part_index_to_node[parent_part_index]
      part_index_to_node[parent_part_index].children.append(part_index_to_node[child_part_index])

  # debug
  print 'token_nodes:'
  for node in token_nodes:
    print 'position = {}, parent_position = {}, pos = {}, len(children) = {}, relation = {}'.format(node.position, node.parent.position if node.parent else 'nothing', node.pos, len(node.children), node.relation) 
  print

  # if the gfl query is valid, all nodes should have a parent,
  # except for the query root which should have parent = None
  root_node = None
  for node in token_nodes:
    # bad query
    if node.parent == None and root_node != None:
      print 'GFL++ query contains multiple roots!'
      return None
    # set root when you find it
    if node.parent == None and root_node == None:
      root_node = node
      # the root should have children
      if len(token_nodes) > 1 and len(root_node.children) == 0:
        print 'root node has no children!'
        return None

  # bad query
  if root_node == None:
    print 'GFL++ query has no root!'
    return None

  # return the root node of the query
  return root_node

if __name__ == '__main__':
  sys.stdout = codecs.getwriter('utf-8')(sys.stdout)
  sys.stderr = codecs.getwriter('utf-8')(sys.stderr)

  print 'Reading the treebanks...'
  treebanks = read_conll_treebanks()
  print 'Extracting patterns...'
  all_patterns = extract_all_patterns(treebanks)

  # debug
  print 'Extracted patterns are:'
  print_all_patterns(treebanks, all_patterns)

  while True:
    print             '======================================================================================'
    query = raw_input('Type a GFL++ query (e.g., NOUN >nsubj VERB <dobj NOUN), or hit the return key to exit:')
    if len(query) == 0:
      print 'Thanks for using the universal dependencies analyzer! Good bye!'
      break
    query_pattern = parse_gfl_query(query)
    if query_pattern == None:
      print 'ERROR: invalid GFL++ query. Please try again.'
    else:
      print 'the specified syntactic pattern is', query_pattern
      print 'pattern found in', len(all_patterns[query_pattern]), 'languages.'
      for language in all_patterns[query_pattern].keys():
        print '\nlanguage and number of times the pattern happens in the language:', language, len(all_patterns[query_pattern][language])
        for sent_id in set(all_patterns[query_pattern][language]):
          more = raw_input('\n Type "show" (or anything else) if you want to see (more) example sentences in this language (i.e., {}), or hit the return key to move on:'.format(language))
          if len(more) == 0:
            break
          sent = treebanks[language][sent_id]
          print 'example sentence:'
          print_sentence(sent, sys.stdout)
