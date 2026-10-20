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
    return {'symbol': name, 'callers': callers, 'tests': tests,
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


def assemble(workspace, spec):
    """Assemble the codebase context of a task attempt."""
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
        item = dict(entry)
        found = structure(root / entry['path'])
        item['symbols'] = found['symbols']
        item['structure_kind'] = found['kind']
        if found.get('reason'):
            item['structure_reason'] = found['reason']
        piece = excerpt(root / entry['path'], found['symbols'], budget)
        if piece is not None:
            item['excerpt'] = piece
            excerpt_bytes += piece['bytes']
            budget -= piece['bytes']
        detailed.append(item)
    # The relation search relates each selected symbol to the code that calls
    # it and the test files that cover it. It is a static reference, not a
    # proven call, and it is bounded like every other part of the map.
    search = search_references(files, [item['path'] for item in detailed], root)
    references = search['references']
    caller_count = 0
    test_count = 0
    for item in detailed:
        relations = symbol_relations(item, references, search['facts']['searched_files'])
        item['relations'] = relations
        for relation in relations:
            caller_count += len(relation['callers'])
            test_count += len(relation['tests'])
    facts = search['facts']
    facts['caller_count'] = caller_count
    facts['test_count'] = test_count
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
                   'max_skipped_reference_files': MAX_SKIPPED_REFERENCE_FILES},
    }


def summary(context, limit=SUMMARY_LIMIT):
    """Return a bounded digest of the assembled codebase context."""
    searched = (context.get('relations') or {}).get('searched_files') or 0
    blocks = []
    for entry in context.get('selected') or []:
        names = ', '.join(symbol['name'] for symbol in entry.get('symbols') or [])
        lines = ['%s (%s, score %s): %s' % (
            entry['path'], entry.get('reason'), entry.get('score'), names or 'no symbol')]
        relations = entry.get('relations') or []
        for relation in relations[:MAX_SUMMARY_SYMBOL_LINES]:
            lines.append('  %s' % _relation_line(relation, searched))
        if len(relations) > MAX_SUMMARY_SYMBOL_LINES:
            lines.append('  (%d more symbols of this file are not shown)'
                         % (len(relations) - MAX_SUMMARY_SYMBOL_LINES))
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
        text += '\n[truncated] %s' % ' and '.join(notes)
    return text


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
