import urllib
import feedparser
import re
import tarfile
import shutil
import os
import time

def decomment(line):
  """
  Remove commented part within a line of a latex file.
  """
  if not re.search(r'\%', line):
    return line
  match = re.search(r'([^\n%]*)(.*)', line)
  newline = match.group(1)
  line = match.group(2)
  while re.search(r'\\$', newline):
    if len(line)==0:
      break
    match = re.search(r'([^\n%]*)(.*)', line[1:])
    newline += '%'+match.group(1)
    line = match.group(2)
  return newline+'\n'

def expand_input(file):
  if not os.path.isfile(file):
    print 'File does not exist.'
    return
  with open(file, 'r') as f:
    unread = f.readlines()
  content = []
  kill_time = 30
  start_time = time.time()
  while len(unread)>0:
    current = unread[0]
    unread = unread[1:]
    if re.search(r'\\input', decomment(current)):
      current = decomment(current)
      match = re.search(r'(.*)\\input{([^}]+)}(.*)', current)
      if not match:
        match = re.search(r'(.*)\\input\s+([\S]+)(.*)', current)
      if match:
        input_file = re.sub(r'^\s*./','',match.group(2))
        input_file = input_file.replace('.tex','')
        input_file = '%s/%s.tex' % (os.getcwd(), input_file)
        if os.path.exists(input_file):
          with open(input_file, 'r') as finput:
            unread = [match.group(1)] + finput.readlines() + [match.group(3)+'\n'] + unread
      else:
        content.append(current)
    else:
      content.append(current)
    if time.time()-start_time > kill_time:
      print 'Error in expanding input files. Output the original main file.'
      with open(file, 'r') as f:
        return f.readlines()
  return content

class arxiv_paper:
  """
  A class for extracting and storing information of papers on arxiv. Currently only supports papers from 2007/03.
  """
  def __init__(self, paper_id, download_source_file = False):
    query = 'http://export.arxiv.org/api/query?id_list=%s' %paper_id
    feedparser._FeedParserMixin.namespaces['http://a9.com/-/spec/opensearch/1.1/'] = 'opensearch'
    feedparser._FeedParserMixin.namespaces['http://arxiv.org/schemas/atom'] = 'arxiv'
    response = urllib.urlopen(query).read()
    feed = feedparser.parse(response)
    entry = feed.entries[0]
    # information
    if entry.title == 'Error':
      print 'Paper %s does not exist.' % paper_id
      return
    self.id = paper_id
    self.title = entry.title.replace('\n', ' ')
    self.title = re.sub(r'\s+', ' ', self.title)
    self.title = self.title.encode('utf8')
    self.subcategory = entry.tags[0]['term']
    self.subcategory = self.subcategory.encode('utf8')
    self.category = re.search(r"([^\.]*)\.?", self.subcategory).group(1)
    self.abstract = entry.summary.replace('\n', ' ')
    self.abstract = re.sub(r'\s+', ' ', self.abstract)
    self.abstract = self.abstract.encode('utf8')
    # download source file
    if download_source_file:
      tarball = '%s.tar.gz' % paper_id
      urllib.urlretrieve('http://arxiv.org/e-print/%s' % paper_id, tarball)
      tar = tarfile.open(tarball)
      tar.extractall('./%s' %paper_id)
      main_file = None
      cwd = os.getcwd()
      os.chdir('%s/%s' % (cwd, paper_id))
      for file in filter(lambda x: '.tex' in x, tar.getnames()):
        f = open(file, 'r')
        for line in f:
          if re.search(r'^[^\%]*\\begin{document}', line):
            main_file = file
            break
        f.close()
      if not main_file:
        print 'No main file found for paper %s' %paper_id
      tar.close()
      self.source_file = expand_input(main_file)
      os.chdir(cwd)
      shutil.rmtree('./%s' %paper_id)
      os.remove('%s.tar.gz' %paper_id)     

  def write_abstract(self, output=None):
    """
    """
    if not output:
      output = '%s.txt' % self.id
    f = open(output, 'w')
    f.write(self.abstract)
    f.close()
