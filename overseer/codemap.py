"""A bounded map of the workspace and the structure of its relevant files.

The map is assembled from the file tree alone. No command is run, and every
bound is explicit: the walk is capped, the files that are read for their
structure are capped, a file that is too large or not text is left alone, and
the excerpt of a symbol and the relation of a symbol to its callers and its
tests are each capped by their own budget. A file whose name marks it as a
secret is never opened.
"""
import ast
import os
from pathlib import Path
import re

IGNORED_DIRECTORIES = frozenset({
    '.git', '.hg', '.svn', '.bzr', 'node_modules', '__pycache__', '.venv', 'venv',
    '.tox', '.mypy_cache', '.pytest_cache', '.ruff_cache', 'dist', 'build', 'target',
    '.next', '.nuxt', '.cache', 'vendor', '.gradle', '.idea', '.vscode', 'coverage',
})
SOURCE_SUFFIXES = frozenset({
    '.py', '.pyi', '.js', '.jsx', '.mjs', '.ts', '.tsx', '.go', '.rs', '.java', '.kt',
    '.c', '.h', '.cc', '.cpp', '.hpp', '.cs', '.rb', '.php', '.swift', '.scala', '.sh',
    '.bash', '.lua', '.pl', '.r',
})
DOCUMENT_SUFFIXES = frozenset({'.md', '.rst', '.txt', '.adoc'})
CONFIG_SUFFIXES = frozenset({'.toml', '.json', '.yaml', '.yml', '.ini', '.cfg', '.lock'})

MAX_FILES = 4000
MAX_DEPTH = 12
MAX_FILE_BYTES = 512 * 1024
MAX_SELECTED = 12
MAX_SYMBOLS = 80
SUMMARY_LIMIT = 4000
# The bounds of the code an attempt is shown. They are what keeps a context
# from flooding: bytes per file, lines per file, ranges per file, and bytes
# for the whole attempt.
MAX_EXCERPT_BYTES = 8 * 1024
MAX_EXCERPT_LINES = 60
MAX_EXCERPT_RANGES = 12
MAX_EXCERPT_TOTAL_BYTES = 32 * 1024
# The bounds of the relation search: the files it may open, the bytes it may
# read, and the relations it may record for one symbol. The search has its own
# budget and adds no file content to the map.
MAX_REFERENCE_FILES = 400
MAX_REFERENCE_BYTES = 2 * 1024 * 1024
MAX_CALLERS_PER_SYMBOL = 20
MAX_TESTS_PER_SYMBOL = 10
MAX_SKIPPED_REFERENCE_FILES = 20
# The lines of one file's relations that the digest shows.
MAX_SUMMARY_SYMBOL_LINES = 6
# The bounds of the memory attachment: the recalled records kept for one
# symbol and for one file, the characters of a record's entry kept, the
# unattached records listed, and the memory lines one file adds to the digest.
MAX_MEMORY_RECORDS_PER_SYMBOL = 5
MAX_MEMORY_RECORDS_PER_FILE = 5
MAX_MEMORY_ENTRY_CHARS = 160
MAX_UNATTACHED_MEMORY_RECORDS = 32
MAX_SUMMARY_MEMORY_LINES = 6
# The bounds of the widening: the files it may add to the selection, and the
# left-out candidates it lists.
MAX_WIDENED_FILES = 4
MAX_WIDEN_LEFT_OUT = 20
MAX_WIDEN_RECORD_IDS = 5
MAX_WIDEN_SYMBOLS = 6
# A file whose name marks it as a secret is never read for its content.
SECRET_SUFFIXES = ('.pem', '.key', '.p12', '.pfx', '.jks', '.keystore', '.ppk',
                    '.asc', '.gpg', '.kdbx')
SECRET_NAMES = frozenset({
    'id_rsa', 'id_dsa', 'id_ecdsa', 'id_ed25519', 'credentials', 'credentials.json',
    'secrets.json', '.npmrc', '.pypirc', '.netrc', 'auth.json', 'token.json',
})
WORD = re.compile(r'[a-z0-9]{3,}')
PATH_LIKE = re.compile(r'[A-Za-z0-9_./-]*[A-Za-z0-9_.-]+\.[A-Za-z0-9]{1,10}')
IDENTIFIER = re.compile(r'[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*')
COMMENT_MARKERS = ('#', '//', '--', '/*', '*')
DECLARATIONS = (
    ('type', re.compile(
        r'^[ \t]*(?:export[ \t]+)?(?:default[ \t]+)?(?:public[ \t]+|private[ \t]+|'
        r'protected[ \t]+|internal[ \t]+|static[ \t]+|abstract[ \t]+|sealed[ \t]+|'
        r'partial[ \t]+)*(?:class|interface|struct|enum|record|trait)[ \t]+'
        r'([A-Za-z_][\w]*)', re.M)),
    ('namespace', re.compile(
        r'^[ \t]*(?:export[ \t]+)?(?:namespace|module|package)[ \t]+([A-Za-z_][\w]*)', re.M)),
    ('function', re.compile(
        r'^[ \t]*(?:export[ \t]+)?(?:async[ \t]+)?(?:def|function|func|fn|sub|proc|'
        r'method|fun)[ \t]+([A-Za-z_][\w]*)', re.M)),
    ('type', re.compile(
        r'^[ \t]*(?:export[ \t]+)?(?:type|typedef)[ \t]+([A-Za-z_][\w]*)', re.M)),
)
STOP_WORDS = frozenset({
    'and', 'the', 'for', 'with', 'that', 'this', 'from', 'into', 'when', 'then',
    'they', 'them', 'their', 'have', 'has', 'was', 'were', 'are', 'not', 'but',
    'you', 'your', 'its', 'each', 'every', 'some', 'any', 'all', 'can', 'will',
    'should', 'would', 'could', 'must', 'one', 'two', 'use', 'using', 'used',
    'add', 'new', 'old', 'run', 'runs', 'make', 'made', 'get', 'set', 'let',
    'out', 'own', 'same', 'also', 'only', 'over', 'under', 'between', 'because',
    # the words a command brings with it are not terms of the task
    'import', 'pathlib', 'environ', 'python', 'usr', 'bin', 'lib', 'sys',
    'json', 'none', 'true', 'false', 'str', 'int', 'bool', 'bytes', 'print',
})


def kind_of(path):
    """Return the kind of a file from its name alone."""
    suffix = Path(path).suffix.lower()
    if suffix in SOURCE_SUFFIXES:
        return 'source'
    if suffix in DOCUMENT_SUFFIXES:
        return 'document'
    if suffix in CONFIG_SUFFIXES:
        return 'config'
    return 'other'


def scan(workspace):
    """Return the files of a workspace, bounded, with the real reason if none."""
    root = Path(workspace)
    if not root.is_dir():
        return [], True, 'the workspace is not a readable directory'
    files = []
    truncated = False
    base = root.resolve()
    for path, directories, names in os.walk(base, followlinks=False):
        directories[:] = sorted(name for name in directories if name not in IGNORED_DIRECTORIES)
        relative = Path(path).relative_to(base)
        if len(relative.parts) >= MAX_DEPTH:
            directories[:] = []
        for name in sorted(names):
            if len(files) >= MAX_FILES:
                truncated = True
                break
            try:
                size = (Path(path) / name).stat().st_size
            except OSError:
                continue
            files.append({'path': str((relative / name).as_posix()) if relative.parts else name,
                          'bytes': size, 'kind': kind_of(name)})
        if truncated:
            break
    return files, truncated, None


def structure(path):
    """Return the structural symbols of one file, or the reason there are none."""
    if is_secret(path):
        return {'kind': 'secret', 'symbols': [],
                'reason': 'the file name marks it as a secret'}
    try:
        size = path.stat().st_size
    except OSError as error:
        return {'kind': 'unreadable', 'symbols': [], 'reason': str(error)}
    if size > MAX_FILE_BYTES:
        return {'kind': 'too large', 'symbols': [],
                'reason': 'the file is larger than %d bytes' % MAX_FILE_BYTES}
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return {'kind': 'not text', 'symbols': [], 'reason': 'the file is not readable text'}
    if '\0' in text[:8192]:
        return {'kind': 'not text', 'symbols': [], 'reason': 'the file holds binary data'}
    if path.suffix.lower() in {'.py', '.pyi'}:
        return {'kind': 'python', 'symbols': _python_symbols(text), 'reason': None}
    return {'kind': 'declarations', 'symbols': _declared_symbols(text), 'reason': None}


def is_secret(path):
    """Report whether a file's name marks it as a secret."""
    name = Path(path).name.casefold()
    if name in SECRET_NAMES or name.startswith('.env'):
        return True
    if any(name.endswith(suffix) for suffix in SECRET_SUFFIXES):
        return True
    return 'secret' in name or 'credential' in name or 'password' in name


def excerpt(path, symbols, budget):
    """Return a bounded excerpt of the code of a file's symbols.

    The excerpt names the line ranges it holds, so a reader can find the code
    in the file itself. A file whose name marks it as a secret is never read.
    """
    if is_secret(path):
        return {'skipped': 'the file name marks it as a secret', 'lines': [], 'bytes': 0,
                'text': '', 'truncated': False}
    if not symbols:
        return None
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return None
    if '\0' in text[:8192]:
        return None
    all_lines = text.splitlines()
    ranges = []
    for symbol in symbols:
        start = int(symbol.get('line') or 0)
        if start < 1:
            continue
        end = int(symbol.get('end') or 0) or min(len(all_lines), start + 4)
        end = max(start, min(end, len(all_lines)))
        ranges.append((start, end))
    if not ranges:
        return None
    ranges.sort()
    merged = []
    for start, end in ranges:
        if merged and start <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    merged = merged[:MAX_EXCERPT_RANGES]
    kept = []
    lines = []
    used = 0
    truncated = False
    for start, end in merged:
        chunk = all_lines[start - 1:end]
        if len(lines) + len(chunk) > MAX_EXCERPT_LINES:
            chunk = chunk[:max(0, MAX_EXCERPT_LINES - len(lines))]
            truncated = True
        for line in chunk:
            if used + len(line) + 1 > MAX_EXCERPT_BYTES or used + len(line) + 1 > budget:
                truncated = True
                break
            lines.append(line)
            used += len(line) + 1
        if chunk:
            kept.append([start, start + len(chunk) - 1])
        if truncated:
            break
    if not lines:
        return None
    return {'lines': kept, 'bytes': used, 'text': '\n'.join(lines), 'truncated': truncated}


def _python_symbols(text):
    """Return the module level classes and functions of a Python file."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError) as error:
        # A source with a null byte raises a ValueError before Python 3.12.
        line = getattr(error, 'lineno', None) or 0
        return [{'name': 'syntax error', 'kind': 'error', 'line': line, 'end': line}]
    symbols = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            end = getattr(node, 'end_lineno', None) or node.lineno
            symbols.append({'name': node.name, 'kind': 'class', 'line': node.lineno,
                            'end': end})
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    child_end = getattr(child, 'end_lineno', None) or child.lineno
                    symbols.append({'name': '%s.%s' % (node.name, child.name),
                                    'kind': 'method', 'line': child.lineno, 'end': child_end})
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = getattr(node, 'end_lineno', None) or node.lineno
            symbols.append({'name': node.name, 'kind': 'function', 'line': node.lineno,
                            'end': end})
    return symbols[:MAX_SYMBOLS]


def _declared_symbols(text):
    """Return the declarations a text file names, for a file that is not Python."""
    symbols = []
    for kind, pattern in DECLARATIONS:
        for match in pattern.finditer(text):
            name = match.group(1)
            if not name:
                continue
            line = text.count('\n', 0, match.start()) + 1
            symbols.append({'name': name, 'kind': kind, 'line': line, 'end': line + 3})
            if len(symbols) >= MAX_SYMBOLS:
                return symbols
    symbols.sort(key=lambda symbol: (symbol['line'], symbol['name']))
    return symbols[:MAX_SYMBOLS]


def is_test_file(path):
    """Report whether a path names a test file, by the path convention alone."""
    for part in Path(path).parts:
        if part in ('test', 'tests'):
            return True
    name = Path(path).name
    if name.startswith('test_') or name.endswith('_test') or name.endswith('Test'):
        return True
    return '.test.' in name or '.spec.' in name


def python_references(text):
    """Return the references a Python file makes, by the name they use.

    A module level symbol is referenced by a name, a method by an attribute.
    The map cannot resolve the object an attribute belongs to, so the kind of
    a method reference says so.
    """
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError) as error:
        # A source with a null byte raises a ValueError before Python 3.12.
        return None
    called = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            called.add(id(node.func))
    names = {}
    attributes = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            kind = 'call' if id(node) in called else 'name'
            names.setdefault(node.id, []).append({'line': node.lineno, 'kind': kind})
        elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load):
            kind = 'call' if id(node) in called else 'attribute'
            attributes.setdefault(node.attr, []).append({'line': node.lineno, 'kind': kind})
    return {'names': names, 'attributes': attributes}


def textual_references(text):
    """Return the identifiers a file that is not Python mentions.

    A match is a mention, not a call: it may be a comment, a string, or an
    unrelated identifier. The lines that are comments are left out.
    """
    mentions = {}
    for number, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith(COMMENT_MARKERS):
            continue
        for match in IDENTIFIER.finditer(line):
            chain = match.group(0)
            mentions.setdefault(chain, []).append({'line': number, 'kind': 'mention'})
            if '.' in chain:
                for part in chain.split('.')[1:]:
                    mentions.setdefault(part, []).append({'line': number, 'kind': 'mention'})
    return mentions


def _file_references(path, text):
    """Return the references of one file, and the way they were found."""
    if path.suffix.lower() in {'.py', '.pyi'}:
        parsed = python_references(text)
        if parsed is not None:
            return {'how': 'parsed', 'names': parsed['names'],
                    'attributes': parsed['attributes'], 'chains': {}, 'fallback': None}
        return {'how': 'textual', 'names': {}, 'attributes': {},
                'chains': textual_references(text),
                'fallback': ('the file does not parse as Python, so its references were '
                             'matched textually')}
    return {'how': 'textual', 'names': {}, 'attributes': {},
            'chains': textual_references(text), 'fallback': None}


def relation_corpus(files, selected_paths):
    """Return the files the relation search may open, in a fixed order.

    The selected files come first, then the test files of the workspace, then
    the other source files. The order is the same on every run.
    """
    corpus = []
    seen = set()
    for path in selected_paths:
        if path not in seen:
            seen.add(path)
            corpus.append(path)
    tests = []
    sources = []
    for entry in files:
        path = entry['path']
        if path in seen:
            continue
        if is_test_file(path):
            tests.append(path)
        elif entry['kind'] == 'source':
            sources.append(path)
    return corpus + sorted(tests) + sorted(sources)


def search_references(files, selected_paths, root):
    """Search the workspace for the references to the selected symbols.

    The search reads and does nothing else. A file whose name marks it as a
    secret is never opened, and a file that is binary, too large, or not text
    is left alone with the reason recorded. The byte budget is checked against
    the size of a file before it is opened, so the bytes read never pass the
    bound.
    """
    corpus = relation_corpus(files, selected_paths)
    references = {}
    skipped = []
    left_out = 0
    bytes_read = 0
    opened = 0
    searched = 0
    truncated = False
    # Every secret named file of the workspace is kept unopened. The count is
    # taken from the file tree alone, so it holds whether or not the file was
    # a candidate of the search.
    secrets = sum(1 for entry in files if is_secret(entry['path']))
    for path in corpus:
        if opened >= MAX_REFERENCE_FILES or bytes_read >= MAX_REFERENCE_BYTES:
            truncated = True
            break
        target = root / path
        if is_secret(target):
            left_out += 1
            _record_skip(skipped, path, 'the file name marks it as a secret')
            continue
        try:
            size = target.stat().st_size
        except OSError as error:
            left_out += 1
            _record_skip(skipped, path, 'the file could not be read: %s' % error)
            continue
        if size > MAX_FILE_BYTES:
            left_out += 1
            _record_skip(skipped, path, 'the file is larger than %d bytes' % MAX_FILE_BYTES)
            continue
        if bytes_read + size > MAX_REFERENCE_BYTES:
            # The size of the file is checked before it is opened, so the
            # bytes read never pass the bound.
            truncated = True
            left_out += 1
            _record_skip(skipped, path, 'the relation search reached its byte budget')
            break
        opened += 1
        try:
            text = target.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            left_out += 1
            _record_skip(skipped, path, 'the file is not readable text')
            continue
        if '\0' in text:
            left_out += 1
            _record_skip(skipped, path, 'the file holds binary data')
            continue
        bytes_read += size
        searched += 1
        references[path] = _file_references(target, text)
    inventory = sorted(entry['path'] for entry in files if is_test_file(entry['path']))
    reason = None
    if truncated:
        reason = ('the search stopped after %d of the %d candidate files, and the '
                  'relation outside the searched set is not represented'
                  % (searched, len(corpus)))
    elif left_out == 1:
        reason = ('one candidate file was left out of the search, and the relation it '
                  'holds is not represented')
    elif left_out:
        reason = ('%d candidate files were left out of the search, and the relation '
                  'they hold is not represented' % left_out)
    facts = {
        'candidate_files': len(corpus),
        'searched_files': searched,
        'opened_files': opened,
        'truncated': truncated,
        'bytes_read': bytes_read,
        'test_file_count': len(inventory),
        'test_files': inventory[:MAX_REFERENCE_FILES],
        'test_files_truncated': len(inventory) > MAX_REFERENCE_FILES,
        'secrets_excluded': secrets,
        'skipped': skipped,
        'reason': reason,
    }
    return {'facts': facts, 'references': references}


def _record_skip(skipped, path, reason):
    """Keep one skipped file, up to the bound of the skipped records."""
    if len(skipped) < MAX_SKIPPED_REFERENCE_FILES:
        skipped.append({'file': path, 'reason': reason})


def symbol_relations(entry, references, searched_files):
    """Return the relation of every symbol of one selected file.

    A relation is a static reference, not a proven call. Python is parsed;
    every other language is matched textually and says so.
    """
    path = entry['path']
    relations = []
    for symbol in entry.get('symbols') or []:
        relations.append(_relation_of(symbol, path, references, searched_files))
    return relations


def _relation_of(symbol, path, references, searched_files):
    """Return the callers and the tests that reference one symbol."""
    name = symbol.get('name') or ''
    bare = name.rsplit('.', 1)[-1]
    start = int(symbol.get('line') or 0)
    end = int(symbol.get('end') or 0)
    callers = []
    tests = []
    for other in references:
        found = references[other]
        how = found['how']
        if how == 'parsed':
            if '.' in name:
                hits = found['attributes'].get(bare) or []
            else:
                hits = found['names'].get(name) or []
            by_bare = False
        else:
            hits = found['chains'].get(name) or []
            by_bare = False
            if not hits and '.' in name:
                # The qualified name was not found, so the bare name of the
                # method is tried. The object it belongs to cannot be
                # resolved, and the entry says so.
                hits = found['chains'].get(bare) or []
                by_bare = bool(hits)
        for hit in hits:
            line = hit['line']
            # A reference inside the definition of the symbol is the
            # definition, not a caller.
            if other == path and start and start <= line <= end:
                continue
            record = {'file': other, 'line': line, 'kind': hit['kind'], 'how': how,
                      'reason': _reference_reason(hit['kind'], how, found.get('fallback'),
                                                 by_bare)}
            if is_test_file(other):
                tests.append(record)
            else:
                callers.append(record)
    caller_total = len(callers)
    test_total = len(tests)
    callers = callers[:MAX_CALLERS_PER_SYMBOL]
    tests = tests[:MAX_TESTS_PER_SYMBOL]
    reasons = []
    if not callers and not tests:
        reasons.append('no reference to the symbol was found in the %d searched files'
                       % searched_files)
    elif not callers:
        reasons.append('no caller outside the test files references the symbol in the '
                       '%d searched files' % searched_files)
    elif not tests:
        reasons.append('no test file references the symbol in the %d searched files'
                       % searched_files)
    if caller_total > len(callers):
        reasons.append('the caller list is truncated at %d of %d references'
                       % (len(callers), caller_total))
    if test_total > len(tests):
        reasons.append('the test list is truncated at %d of %d references'
                       % (len(tests), test_total))
    return {'symbol': name, 'callers': callers, 'tests': tests, 'caller_total': caller_total,
            'reason': '; '.join(reasons) or None}


def _reference_reason(kind, how, fallback, by_bare=False):
    """Return the reason that states what a reference is worth."""
    parts = []
    if fallback:
        parts.append(fallback)
    if kind == 'call':
        parts.append('the reference is the callee of a call')
    elif kind == 'attribute':
        parts.append('the reference is to an attribute of that name, and the map '
                     'cannot resolve the object it belongs to')
    elif kind == 'name':
        parts.append('the reference names the symbol, and it is not a call')
    else:
        parts.append('the match is textual, and it may be a comment, a string, or an '
                     'unrelated identifier')
    if by_bare:
        parts.append('the match is by the bare name of the method, and the map cannot '
                     'resolve the object it belongs to')
    return '; '.join(parts)


MEMORY_MATCH_REASON = ('the record names the symbol by its text; a textual match does not '
                       'prove the record is about this symbol')
MEMORY_FILE_REASON = ('the record names the file by its path and none of its symbols; a '
                      'textual match does not prove the record is about this file')


def _identifier_shaped(name):
    """Return whether a name reads as an identifier rather than an English word."""
    return '_' in name or '.' in name or any(char.isupper() for char in name[1:])


def _name_spans(name, text):
    """Return the spans where a name occurs in a text on identifier boundaries."""
    pattern = re.compile(r'(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])' % re.escape(name))
    return [match.span() for match in pattern.finditer(text)]


def _path_pattern(path):
    """Return the pattern of a workspace path on path boundaries.

    A trailing '.' or ',' of a sentence is not part of the path, but a '.'
    that starts a longer suffix is.
    """
    return re.compile(r'(?<![A-Za-z0-9_./-])%s(?![A-Za-z0-9_/-])(?!\.[A-Za-z0-9_])'
                      % re.escape(path))


def _mask_paths(text, paths):
    """Return a text with the selected paths it names blanked out.

    A path such as 'pkg/build.py' holds the identifier 'build' between its
    separators, and that is the name of the file, not a mention of a symbol.
    """
    for path in sorted(paths, key=len, reverse=True):
        text = _path_pattern(path).sub(lambda match: ' ' * len(match.group(0)), text)
    return text


def _names_in(text, names, shaped_only):
    """Return the names a text names, the most specific name winning.

    An occurrence of a name inside the occurrence of a longer name, such as
    'WidgetFilter' inside 'WidgetFilter.apply', belongs to the longer name.
    """
    if not text:
        return set()
    spans = {}
    for name in names:
        if shaped_only and not _identifier_shaped(name):
            continue
        found = _name_spans(name, text)
        if found:
            spans[name] = found
    named = set()
    for name, found in spans.items():
        for start, end in found:
            inside = any(other != name and len(other) > len(name)
                         and other_start <= start and end <= other_end
                         for other, other_spans in spans.items()
                         for other_start, other_end in other_spans)
            if not inside:
                named.add(name)
                break
    return named


def _unusable_clause(record):
    """Return why a recalled record is not usable, or None when it is."""
    if record.get('informs_decision') is True:
        return None
    status = record.get('status')
    if status == 'superseded':
        by = record.get('superseded_by')
        return 'the decision was superseded%s and is not usable' % (
            ' by %s' % by if by else '')
    if status == 'invalidated':
        revision = record.get('revision')
        return ("the fact is bound to revision %s, which is not the workspace's base "
                'commit, and it is not usable' % (revision or 'unknown'))
    if status == 'unverified':
        return 'the record is a hypothesis, unverified, and it is not usable'
    if status == 'historical':
        return ('the record is a past attempt, a result and not current state, and it is '
                'not usable')
    return 'the record does not inform a decision, and it is not usable'


def _attachment(record, matched, field, base_reason):
    """Return the attachment of one record to one symbol or file."""
    entry = ' '.join(str(record.get('entry') or '').split())[:MAX_MEMORY_ENTRY_CHARS]
    clause = _unusable_clause(record)
    return {
        'record_id': record.get('record_id'),
        'kind': record.get('kind'),
        'status': record.get('status'),
        'usable': clause is None,
        'superseded_by': record.get('superseded_by') if record.get('kind') == 'decision'
                         else None,
        'matched': matched,
        'field': field,
        'how': 'textual',
        'entry': entry,
        'reason': base_reason + ('; ' + clause if clause else ''),
    }


def _keep(holder, found, cap, reason_key):
    """Order the attachments of one holder and keep at most cap of them.

    The usable records come first, then the rest; inside each group the
    recall's order is kept, so a usable record is never crowded out.
    """
    found.sort(key=lambda pair: (not pair[1]['usable'], pair[0],
                                 str(pair[1]['record_id'])))
    holder['memory'] = [attachment for _, attachment in found[:cap]]
    holder['memory_dropped'] = max(0, len(found) - cap)
    kept = [order for order, _ in found[:cap]]
    if holder['memory_dropped']:
        note = ('the memory list is truncated at %d of %d records'
                % (cap, len(found)))
        holder[reason_key] = '; '.join(part for part in (holder.get(reason_key), note)
                                       if part)
    return kept


def attach_memory(selected, records):
    """Attach recalled memory records to the selected symbols they name.

    The records are plain dicts. The match is textual, case-sensitive, and on
    identifier boundaries, so it does not prove that a record is about a
    symbol. Every eligible name is matched in the record's affected component;
    only an identifier-shaped name, one with '_' or '.' or a capital after its
    first character, is matched in its entry, because a plain lowercase word in
    free text is far more often an English word than a symbol. Every status
    attaches, and a record that does not inform a decision is marked not
    usable. A record that names no selected symbol and no selected file is
    counted as unattached. The counts describe the attachments the caps kept,
    and a record every attachment of which a cap dropped is counted apart.
    Nothing is read from a file or a ledger.
    """
    records = list(records or [])
    owners = {}
    for entry in selected:
        for relation in entry.get('relations') or []:
            relation['memory'] = []
            relation['memory_dropped'] = 0
        entry['memory'] = []
        entry['memory_dropped'] = 0
        kinds = {symbol.get('name'): symbol.get('kind') for symbol in entry.get('symbols') or []}
        for relation in entry.get('relations') or []:
            name = relation.get('symbol') or ''
            if kinds.get(name) == 'error' or len(name) < 3:
                continue
            owners.setdefault(name, []).append((entry, relation))
    names = sorted(owners)
    paths = [entry['path'] for entry in selected]
    found_for = {}
    matched = set()
    unattached = []
    for order, record in enumerate(records):
        component = str(record.get('affected_component') or '')
        text = str(record.get('entry') or '')
        in_component = _names_in(_mask_paths(component, paths), names, shaped_only=False)
        in_entry = _names_in(_mask_paths(text, paths), names, shaped_only=True) - in_component
        hit_files = set()
        hit_any = False
        for field, hits in (('affected_component', in_component), ('entry', in_entry)):
            for name in sorted(hits):
                for entry, relation in owners[name]:
                    attachment = _attachment(record, name, field, MEMORY_MATCH_REASON)
                    found_for.setdefault(id(relation), (relation, []))[1].append(
                        (order, attachment))
                    hit_files.add(entry['path'])
                    hit_any = True
        for entry in selected:
            if entry['path'] in hit_files:
                continue
            for field, value in (('affected_component', component), ('entry', text)):
                if _path_pattern(entry['path']).search(value):
                    attachment = _attachment(record, entry['path'], field, MEMORY_FILE_REASON)
                    found_for.setdefault(id(entry), (entry, []))[1].append((order, attachment))
                    hit_any = True
                    break
        if hit_any:
            matched.add(order)
        else:
            unattached.append({'record_id': record.get('record_id'),
                               'kind': record.get('kind'),
                               'status': record.get('status'),
                               'reason': 'the record names no selected symbol and no '
                                         'selected file'})
    attachments = 0
    dropped = 0
    to_symbols = set()
    to_files = set()
    for holder, found in found_for.values():
        # A file entry's reason is why it was selected, so the cap of its own
        # memory list is noted beside it.
        if 'symbol' in holder:
            to_symbols.update(_keep(holder, found, MAX_MEMORY_RECORDS_PER_SYMBOL, 'reason'))
        else:
            to_files.update(_keep(holder, found, MAX_MEMORY_RECORDS_PER_FILE, 'memory_reason'))
        attachments += len(holder['memory'])
        dropped += holder['memory_dropped']
    attached = to_symbols | to_files
    return {
        'supplied': len(records),
        'attached': len(attached),
        'attached_to_symbols': len(to_symbols),
        'attached_to_files': len(to_files),
        'attachments': attachments,
        'attachments_dropped': dropped,
        'dropped_by_cap': len(matched - attached),
        'not_usable_attached': len([order for order in attached
                                    if _unusable_clause(records[order]) is not None]),
        'unattached': unattached[:MAX_UNATTACHED_MEMORY_RECORDS],
        'unattached_count': len(unattached),
        'unattached_truncated': len(unattached) > MAX_UNATTACHED_MEMORY_RECORDS,
        'how': 'textual',
        'reason': None if records else 'no memory record was supplied',
    }


def _no_memory():
    """Return the memory block of a map that was given no record."""
    return {'supplied': 0, 'attached': 0, 'attached_to_symbols': 0, 'attached_to_files': 0,
            'attachments': 0, 'attachments_dropped': 0, 'dropped_by_cap': 0,
            'not_usable_attached': 0, 'unattached': [],
            'unattached_count': 0, 'unattached_truncated': False, 'how': 'textual',
            'reason': 'no memory record was supplied'}


def task_terms(spec):
    """Return the terms of a task that a file can be relevant by.

    The terms are the task's own words: the objective and the contract. The
    files the commands name are found by path, not by word.
    """
    terms = set()
    objective = spec.get('objective')
    if isinstance(objective, str):
        terms.update(WORD.findall(objective.casefold()))
    contract = spec.get('contract') or {}
    if isinstance(contract, dict):
        for field in ('role', 'project_constraints', 'required_capabilities'):
            value = contract.get(field)
            if isinstance(value, str):
                terms.update(WORD.findall(value.casefold()))
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        terms.update(WORD.findall(item.casefold()))
    return {term for term in terms if term not in STOP_WORDS}


def named_files(spec, workspace):
    """Return the workspace files the task's own commands name."""
    root = Path(workspace).resolve()
    named = []
    for field in ('implementation', 'checks'):
        argv = spec.get(field)
        if not isinstance(argv, list):
            continue
        for argument in argv:
            if not isinstance(argument, str) or len(argument) > 4096:
                continue
            for candidate in _path_candidates(argument):
                candidate = Path(candidate)
                for base in ([candidate] if candidate.is_absolute() else [root / candidate]):
                    try:
                        resolved = base.resolve()
                    except OSError:
                        continue
                    if resolved.is_file() and _inside(resolved, root):
                        relative = str(resolved.relative_to(root))
                        if relative not in named:
                            named.append(relative)
    return named


def _path_candidates(argument):
    """Return the path like substrings of one command argument."""
    candidates = []
    for match in PATH_LIKE.finditer(argument):
        candidate = match.group(0).strip('\'"')
        if not candidate or candidate in candidates:
            continue
        candidates.append(candidate)
        if len(candidates) >= 16:
            break
    return candidates


def _inside(path, root):
    try:
        return os.path.commonpath([str(path), str(root)]) == str(root)
    except ValueError:
        return False


def select(files, terms, named, root):
    """Return the files that are relevant to the task, with the reason."""
    chosen = []
    for name in named:
        for entry in files:
            if entry['path'] == name and entry not in chosen:
                entry = dict(entry)
                entry['score'] = 100
                entry['reason'] = 'the task commands name this file'
                chosen.append(entry)
                break
    scored = []
    for entry in files:
        if any(entry['path'] == item['path'] for item in chosen):
            continue
        haystack = entry['path'].casefold()
        score = sum(1 for term in terms if term in haystack)
        if score:
            scored.append((score, entry))
    scored.sort(key=lambda pair: (-pair[0], pair[1]['path']))
    for score, entry in scored:
        if len(chosen) >= MAX_SELECTED:
            break
        item = dict(entry)
        item['score'] = score
        item['reason'] = 'the path matches the task terms'
        chosen.append(item)
    return chosen[:MAX_SELECTED]


def _widening_decision(record):
    """Return whether a recalled record may widen the selection."""
    return (record.get('kind') == 'decision' and record.get('status') == 'current'
            and record.get('informs_decision') is True)


def widen(files, selected, records):
    """Return the files to add to the selection, and the facts of the widening.

    A file widens the selection when a current decision names its path in the
    record's affected component or entry, by a textual match on path
    boundaries, or when it holds a caller of a symbol of the task's own
    selection, by a static reference. A decision that names a symbol but no
    path does not widen, because the map cannot know the symbols of a file it
    has not read. A verified fact, a superseded decision, a hypothesis, and a
    historical attempt never widen: the decisions are what the attempt is to
    respect, and a fact is evidence about code already in view. A test file
    never widens as a caller; it is the test relation. The widening is one
    round: what a widened file calls or is named by does not widen further.
    It never displaces a file of the task's own selection, adds at most
    MAX_WIDENED_FILES, and records every candidate the bounds left out.
    """
    selected_paths = {entry['path'] for entry in selected}
    known = {entry['path'] for entry in files}
    candidates = {}
    order = []
    for record in records or []:
        if not _widening_decision(record):
            continue
        texts = [str(record.get('affected_component') or ''), str(record.get('entry') or '')]
        # The paths one record names are taken in path order, so the order
        # of the file tree never decides which one the bound keeps.
        for entry in sorted(files, key=lambda item: item['path']):
            path = entry['path']
            if path in selected_paths:
                continue
            if not any(_path_pattern(path).search(text) for text in texts):
                continue
            if path not in candidates:
                candidates[path] = {'path': path, 'decision': [], 'symbols': set(),
                                    'references': 0, 'how': set(), 'named': False}
                order.append(path)
            record_id = record.get('record_id')
            if record_id is not None and record_id not in candidates[path]['decision']:
                candidates[path]['decision'].append(record_id)
            candidates[path]['named'] = True
    capped = 0
    for entry in selected:
        for relation in entry.get('relations') or []:
            if (relation.get('caller_total') or 0) > len(relation.get('callers') or []):
                capped += 1
            for caller in relation.get('callers') or []:
                path = caller.get('file')
                if path in selected_paths or path not in known or is_test_file(path):
                    continue
                if path not in candidates:
                    candidates[path] = {'path': path, 'decision': [], 'symbols': set(),
                                        'references': 0, 'how': set(), 'named': False}
                found = candidates[path]
                found['symbols'].add(relation.get('symbol'))
                found['references'] += 1
                found['how'].add(caller.get('how'))
    decided = [candidates[path] for path in order]
    called = sorted((found for found in candidates.values() if not found['named']),
                    key=lambda found: (-found['references'], found['path']))
    ranked = decided + called
    room = max(0, min(MAX_WIDENED_FILES, MAX_SELECTED - len(selected)))
    added = []
    left_out = []
    secrets = 0
    by_decision = 0
    by_caller = 0
    for found in ranked:
        via = (['decision'] if found['named'] else []) + (['caller'] if found['references'] else [])
        if is_secret(found['path']):
            secrets += 1
            left_out.append({'path': found['path'], 'via': via,
                             'reason': 'the file name marks it as a secret'})
            continue
        if len(added) >= room:
            # The reason names the bound that applied: the room the selection
            # bound left, or the widening bound when it is the smaller.
            if MAX_SELECTED - len(selected) <= 0:
                reason = ('the selection bound of %d was reached by the task\'s own selection'
                          % MAX_SELECTED)
            elif MAX_SELECTED - len(selected) < MAX_WIDENED_FILES:
                reason = ('the selection bound of %d was reached after %d widened files'
                          % (MAX_SELECTED, len(added)))
            else:
                reason = 'the widening bound of %d was reached' % MAX_WIDENED_FILES
            left_out.append({'path': found['path'], 'via': via, 'reason': reason})
            continue
        parts = []
        if found['named']:
            parts.append('a current decision names this file by a textual path match')
        if found['references']:
            parts.append('it holds %d static references to selected symbols'
                         % found['references'])
        item = dict(next(entry for entry in files if entry['path'] == found['path']))
        item.update({
            'score': 0,
            'reason': ('a current decision names this file' if found['named']
                       else 'the file calls a selected symbol'),
            'widened_by': {
                'via': via,
                'record_ids': found['decision'][:MAX_WIDEN_RECORD_IDS],
                'symbols': sorted(found['symbols'])[:MAX_WIDEN_SYMBOLS],
                'references': found['references'],
                'how': sorted(set(found['how']) | ({'textual'} if found['named'] else set())),
                'reason': '; '.join(parts),
            },
        })
        added.append(item)
        if found['named']:
            by_decision += 1
        else:
            by_caller += 1
    reasons = []
    for item in left_out:
        if item['reason'] not in reasons:
            reasons.append(item['reason'])
    if capped:
        # A file that holds only callers past the cap of a caller list is not
        # seen, so it is neither a candidate nor counted as left out.
        reasons.append('the caller lists of %d selected symbols were truncated at %d, and a '
                       'file holding only callers past that cap is not a candidate'
                       % (capped, MAX_CALLERS_PER_SYMBOL))
    reason = '; '.join(reasons) or None
    facts = {
        'primary': len(selected),
        'widened': len(added),
        'widened_by_decision': by_decision,
        'widened_by_caller': by_caller,
        'candidates': len(ranked),
        'left_out': left_out[:MAX_WIDEN_LEFT_OUT],
        'left_out_count': len(left_out),
        'left_out_truncated': len(left_out) > MAX_WIDEN_LEFT_OUT,
        'secrets_left_out': secrets,
        'callers_truncated': capped,
        'reason': reason,
    }
    return {'added': added, 'facts': facts}


def _detail(entry, root, budget):
    """Return a selected entry with its structure and its excerpt, and the bytes spent."""
    item = dict(entry)
    found = structure(root / entry['path'])
    item['symbols'] = found['symbols']
    item['structure_kind'] = found['kind']
    if found.get('reason'):
        item['structure_reason'] = found['reason']
    piece = excerpt(root / entry['path'], found['symbols'], budget)
    spent = 0
    if piece is not None:
        item['excerpt'] = piece
        spent = piece['bytes']
    return item, spent


def assemble(workspace, spec, memory=None):
    """Assemble the codebase context of a task attempt.

    The memory is the list of recalled records, as plain dicts. When it is
    given, each record is attached to the selected symbols and files it names.
    The task's own selection is detailed first and spends the excerpt budget
    first; the files the widening adds are detailed from what is left, and
    their relations come from the same, single relation search. The caller and
    test counts include the widened files' symbols.
    """
    if not workspace:
        return {'version': 1, 'assembled': False, 'reason': 'the task names no workspace',
                'files': [], 'selected': [], 'file_count': 0, 'excerpt_bytes': 0}
    files, truncated, problem = scan(workspace)
    if problem:
        return {'version': 1, 'assembled': False, 'reason': problem, 'files': [],
                'selected': [], 'file_count': 0, 'excerpt_bytes': 0}
    if not files:
        return {'version': 1, 'assembled': False, 'reason': 'the workspace holds no readable file',
                'files': [], 'selected': [], 'file_count': 0, 'excerpt_bytes': 0}
    root = Path(workspace).resolve()
    terms = task_terms(spec)
    named = named_files(spec, workspace)
    selected = select(files, terms, named, root)
    detailed = []
    budget = MAX_EXCERPT_TOTAL_BYTES
    excerpt_bytes = 0
    for entry in selected:
        item, spent = _detail(entry, root, budget)
        item['widened_by'] = None
        excerpt_bytes += spent
        budget -= spent
        detailed.append(item)
    # The relation search relates each selected symbol to the code that calls
    # it and the test files that cover it. It is a static reference, not a
    # proven call, and it is bounded like every other part of the map.
    search = search_references(files, [item['path'] for item in detailed], root)
    references = search['references']
    caller_count = 0
    test_count = 0
    for item in detailed:
        item['relations'] = symbol_relations(item, references, search['facts']['searched_files'])
    # One round of widening, over the relations of the task's own selection.
    widening = widen(files, detailed, memory)
    for entry in widening['added']:
        item, spent = _detail(entry, root, budget)
        excerpt_bytes += spent
        budget -= spent
        item['relations'] = symbol_relations(item, references, search['facts']['searched_files'])
        detailed.append(item)
    for item in detailed:
        for relation in item['relations']:
            caller_count += len(relation['callers'])
            test_count += len(relation['tests'])
    facts = search['facts']
    facts['caller_count'] = caller_count
    facts['test_count'] = test_count
    if memory is None:
        attached = _no_memory()
        for item in detailed:
            item['memory'] = []
            item['memory_dropped'] = 0
            for relation in item['relations']:
                relation['memory'] = []
                relation['memory_dropped'] = 0
    else:
        attached = attach_memory(detailed, memory)
    return {
        'version': 1,
        'assembled': True,
        'workspace': str(workspace),
        'reason': None,
        'file_count': len(files),
        'truncated': truncated,
        'terms': sorted(terms),
        'selected': detailed,
        'excerpt_bytes': excerpt_bytes,
        'relations': facts,
        'memory': attached,
        'selection': widening['facts'],
        'limits': {'max_files': MAX_FILES, 'max_depth': MAX_DEPTH,
                   'max_file_bytes': MAX_FILE_BYTES, 'max_selected': MAX_SELECTED,
                   'max_symbols': MAX_SYMBOLS,
                   'max_excerpt_bytes': MAX_EXCERPT_BYTES,
                   'max_excerpt_lines': MAX_EXCERPT_LINES,
                   'max_excerpt_ranges': MAX_EXCERPT_RANGES,
                   'max_excerpt_total_bytes': MAX_EXCERPT_TOTAL_BYTES,
                   'max_reference_files': MAX_REFERENCE_FILES,
                   'max_reference_bytes': MAX_REFERENCE_BYTES,
                   'max_callers_per_symbol': MAX_CALLERS_PER_SYMBOL,
                   'max_tests_per_symbol': MAX_TESTS_PER_SYMBOL,
                   'max_skipped_reference_files': MAX_SKIPPED_REFERENCE_FILES,
                   'max_memory_records_per_symbol': MAX_MEMORY_RECORDS_PER_SYMBOL,
                   'max_memory_records_per_file': MAX_MEMORY_RECORDS_PER_FILE,
                   'max_memory_entry_chars': MAX_MEMORY_ENTRY_CHARS,
                   'max_unattached_memory_records': MAX_UNATTACHED_MEMORY_RECORDS,
                   'max_summary_memory_lines': MAX_SUMMARY_MEMORY_LINES,
                   'max_widened_files': MAX_WIDENED_FILES,
                   'max_widen_left_out': MAX_WIDEN_LEFT_OUT},
    }


def summary(context, limit=SUMMARY_LIMIT):
    """Return a bounded digest of the assembled codebase context."""
    searched = (context.get('relations') or {}).get('searched_files') or 0
    unattached = (context.get('memory') or {}).get('unattached_count') or 0
    selection = context.get('selection') or {}
    tails = []
    if selection.get('left_out_count'):
        tails.append('selection: %d files widened, %d candidates left out (%s)' % (
            selection.get('widened') or 0, selection['left_out_count'],
            selection.get('reason')))
    if unattached:
        tails.append('memory: %d recalled records name no selected symbol; see '
                     'OVERSEER_RECALL_SUMMARY' % unattached)
    # The tail keeps its own room, and never more room than the digest has.
    tail = '\n'.join(tails)[:limit]
    if tail:
        limit = max(0, limit - len(tail) - 1)
    blocks = []
    for entry in context.get('selected') or []:
        names = ', '.join(symbol['name'] for symbol in entry.get('symbols') or [])
        lines = ['%s (%s, score %s): %s' % (
            entry['path'], _selection_reason(entry), entry.get('score'), names or 'no symbol')]
        relations = entry.get('relations') or []
        total = len(entry.get('memory') or []) + sum(
            len(relation.get('memory') or []) for relation in relations)
        shown = _shown_memory(entry, relations[:MAX_SUMMARY_SYMBOL_LINES])
        for attachment in entry.get('memory') or []:
            if id(attachment) in shown:
                lines.append('  file %s' % _memory_line(attachment))
        for relation in relations[:MAX_SUMMARY_SYMBOL_LINES]:
            lines.append('  %s' % _relation_line(relation, searched))
            for attachment in relation.get('memory') or []:
                if id(attachment) in shown:
                    lines.append('    %s' % _memory_line(attachment))
        if len(relations) > MAX_SUMMARY_SYMBOL_LINES:
            lines.append('  (%d more symbols of this file are not shown)'
                         % (len(relations) - MAX_SUMMARY_SYMBOL_LINES))
        if total > len(shown):
            lines.append('  (%d more memory records of this file are not shown)'
                         % (total - len(shown)))
        blocks.append(lines)
    pieces = []
    dropped = 0
    used = 0
    cut = False
    for index, lines in enumerate(blocks):
        piece = '\n'.join(lines)
        if index == 0:
            pieces.append(piece[:limit])
            used = len(pieces[0])
            cut = len(piece) > limit
            continue
        if used + 1 + len(piece) > limit:
            dropped += 1
            continue
        pieces.append(piece)
        used += 1 + len(piece)
    text = '\n'.join(pieces)
    if cut or dropped:
        notes = []
        if cut:
            notes.append('the relations of the first file were cut')
        if dropped:
            notes.append("%d more files' relations were dropped" % dropped)
        if tail:
            text = text + '\n' + tail if text else tail
        text += '\n[truncated] %s' % ' and '.join(notes)
    elif tail:
        text = text + '\n' + tail if text else tail
    return text


def _selection_reason(entry):
    """Return why a file is in the digest: the task's own reason, or its widening."""
    widened = entry.get('widened_by')
    if not widened:
        return entry.get('reason')
    parts = []
    if 'decision' in widened.get('via', []):
        ids = ', '.join(str(record_id)[:8] for record_id in widened.get('record_ids') or [])
        parts.append('a current decision %s names this file' % ids)
    if 'caller' in widened.get('via', []):
        parts.append('calls %s (%d references)' % (', '.join(widened.get('symbols') or []),
                                                   widened.get('references') or 0))
    return 'widened: ' + '; '.join(parts)


def _shown_memory(entry, relations):
    """Return the attachments of one file that the digest has room for.

    The room is shared by the whole file, and the usable records take it
    first, so a not-usable record of one symbol never crowds out a usable
    record of another. Inside each group the file's own order is kept.
    """
    candidates = list(entry.get('memory') or [])
    for relation in relations:
        candidates.extend(relation.get('memory') or [])
    ranked = sorted(enumerate(candidates),
                    key=lambda pair: (not pair[1].get('usable'), pair[0]))
    return {id(attachment) for _, attachment in ranked[:MAX_SUMMARY_MEMORY_LINES]}


def _memory_line(attachment):
    """Return the one line that carries an attached memory record in the digest."""
    head = 'memory %s/%s %s' % (attachment.get('kind'), attachment.get('status'),
                                str(attachment.get('record_id') or '')[:8])
    if not attachment.get('usable'):
        head += ' NOT USABLE (%s)' % attachment.get('status')
    return '%s: %s (textual match on %s)' % (head, attachment.get('entry'),
                                             attachment.get('field'))


def _relation_line(relation, searched):
    """Return the one line that carries a symbol's relation in the digest."""
    parts = []
    callers = relation.get('callers') or []
    tests = relation.get('tests') or []
    if callers:
        first = callers[0]
        parts.append('caller %s:%d (%s, %s)' % (first['file'], first['line'],
                                                 first['kind'], first['how']))
        if len(callers) > 1:
            parts.append('%d more callers' % (len(callers) - 1))
    if tests:
        first = tests[0]
        parts.append('test %s:%d (%s, %s)' % (first['file'], first['line'],
                                               first['kind'], first['how']))
        if len(tests) > 1:
            parts.append('%d more tests' % (len(tests) - 1))
    if not parts:
        return '%s <- no caller and no test found in the %d searched files' % (
            relation.get('symbol'), searched)
    return '%s <- %s' % (relation.get('symbol'), ', '.join(parts))
