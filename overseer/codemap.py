"""A bounded map of the workspace and the structure of its relevant files.

The map is assembled from the file tree alone. No command is run, no file
content is carried into it, and every bound is explicit: the walk is capped,
the files that are read for their structure are capped, and a file that is too
large or not text is left alone.
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
# A file whose name marks it as a secret is never read for its content.
SECRET_SUFFIXES = ('.pem', '.key', '.p12', '.pfx', '.jks', '.keystore', '.ppk',
                    '.asc', '.gpg', '.kdbx')
SECRET_NAMES = frozenset({
    'id_rsa', 'id_dsa', 'id_ecdsa', 'id_ed25519', 'credentials', 'credentials.json',
    'secrets.json', '.npmrc', '.pypirc', '.netrc', 'auth.json', 'token.json',
})
WORD = re.compile(r'[a-z0-9]{3,}')
PATH_LIKE = re.compile(r'[A-Za-z0-9_./-]*[A-Za-z0-9_.-]+\.[A-Za-z0-9]{1,10}')
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
    if not symbols:
        return None
    if is_secret(path):
        return {'skipped': 'the file name marks it as a secret', 'lines': [], 'bytes': 0,
                'text': '', 'truncated': False}
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
    except SyntaxError as error:
        return [{'name': 'syntax error', 'kind': 'error', 'line': error.lineno or 0,
                 'end': error.lineno or 0}]
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
        'limits': {'max_files': MAX_FILES, 'max_depth': MAX_DEPTH,
                   'max_file_bytes': MAX_FILE_BYTES, 'max_selected': MAX_SELECTED,
                   'max_symbols': MAX_SYMBOLS,
                   'max_excerpt_bytes': MAX_EXCERPT_BYTES,
                   'max_excerpt_lines': MAX_EXCERPT_LINES,
                   'max_excerpt_ranges': MAX_EXCERPT_RANGES,
                   'max_excerpt_total_bytes': MAX_EXCERPT_TOTAL_BYTES},
    }


def summary(context, limit=SUMMARY_LIMIT):
    """Return a bounded digest of the assembled codebase context."""
    lines = []
    for entry in context.get('selected') or []:
        names = ', '.join(symbol['name'] for symbol in entry.get('symbols') or [])
        lines.append('%s (%s, score %s): %s' % (
            entry['path'], entry.get('reason'), entry.get('score'), names or 'no symbol'))
    text = '\n'.join(lines)
    if len(text) > limit:
        text = text[:limit] + '\n[truncated]'
    return text
