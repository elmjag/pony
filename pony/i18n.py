import re, os.path
from itertools import izip, count

import pony
from pony.utils import read_text_file

class I18nParseError(Exception): pass

space_re = re.compile(r'\s+')
lang_re = re.compile(r'([A-Za-z-]+)\s*')
param_re = re.compile(r"\$(?:\w+|\$)")

translations = {}

def translate(key, params, lang_list):
    for lang in lang_list:
        while True:
            try: params_order, lstr = translations[key][lang]
            except KeyError:
                try:
                    lang = lang[:lang.rindex('-')]
                    continue
                except ValueError: break
            result = []
            for flag, value in lstr:
                if flag: result.append(params[params_order.pop(0)])
                else: result.append(value)
            return ''.join(result)
    else: return None

def load(filename):
    text = read_text_file(filename)
    translations.update(parse(text.split('\n')))

def parse(lines):
    d = {}
    for kstr, lstr_list in read_phrases(lines):
        lineno, key = kstr
        t = transform_string(key)
        norm_key = []
        for flag, value in t:
            if flag: norm_key.append('$#')
            else: norm_key.append(value)
        norm_key = ''.join(norm_key)
        norm_key = space_re.sub(' ', norm_key).strip()
        ld = {}        
        params_list = []
        for match in param_re.finditer(key):
            if match.group() != '$$': params_list.append(match.group())
        for lineno2, s in lstr_list:
            s = s.strip()
            m = lang_re.match(s)
            if m is None: raise I18nParseError(
                "No language selector found in line %d (line=%s)" % (lineno2, s))
            langkey = m.group(1)
            lstr = s[m.end():]
            check_params(params_list, lineno, lstr, lineno2, langkey)
            lstr = transform_string(lstr)
            ld[langkey] = (get_params_order(t, lstr), lstr)
        d[norm_key] = ld
    return d

def read_phrases(lines):
   kstr, lstr_list = None, []
   for lineno, line in izip(count(1), lines):
       if not line or line.isspace(): continue
       elif line[0].isspace():
           if kstr is None: raise I18nParseError(
               "Translation string found but key string was expected in line %d" % lineno)
           lstr_list.append((lineno, line))
       elif kstr is None: kstr = lineno, line  # assert lineno == 1
       else:
           yield kstr, lstr_list
           kstr, lstr_list = (lineno, line), []
   if kstr is not None:
       yield kstr, lstr_list

def transform_string(s):
    result = []
    pos = 0
    for match in param_re.finditer(s):
        result.append((False, s[pos:match.start()]))
        if match.group() == '$$': result.append((False, '$'))
        else: result.append((True, match.group()[1:]))
        pos = match.end()
    result.append((False, s[pos:]))
    prevf = None
    result2 = []
    for flag, value in result:
        if flag == prevf == False: result2[-1] = (flag, result2[-1][1] + value)
        elif value: result2.append((flag, value))
        prevf = flag
    return result2

def check_params(params_list, lineno, lstr, lineno2, langkey):
    params_list2 = []
    for match in param_re.finditer(lstr):
        if match.group() != '$$': params_list2.append(match.group())
    if len(params_list) != len(params_list2): raise I18nParseError(
        "Parameters count in line %d doesn't match with line %d" % (lineno, lineno2))
    params_list.sort()
    params_list2.sort()
    for a, b in zip(params_list, params_list2):
        if a != b: raise I18nParseError(
            "Unknown parameter in line %d: %s (translation for %s)" % (lineno2, b, langkey))

def get_params_order(key, lstr):
    pkey, plstr = [], []
    for flag, value in key:
        if flag: pkey.append(value)
    for flag, value in lstr:
        if flag: plstr.append(value)
    result = []
    for v in plstr:
        result.append(pkey.index(v))
    return result

load(os.path.join(pony.PONY_DIR, 'translations.txt'))
