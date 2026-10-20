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


def _python_symbols(text):
    """Return the module level classes and functions of a Python file."""
    try:
        tree = ast.parse(text)
    except SyntaxError as error:
        return [{'name': 'syntax error', 'kind': 'error', 'line': error.lineno or 0}]
    symbols = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            symbols.append({'name': node.name, 'kind': 'class', 'line': node.lineno})
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.append({'name': '%s.%s' % (node.name, child.name),
                                    'kind': 'method', 'line': child.lineno})
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append({'name': node.name, 'kind': 'function', 'line': node.lineno})
    return symbols[:MAX_SYMBOLS]


def _declared_symbols(text):
    """Return the declarations a text file names, for a file that is not Python."""
    symbols = []
    for kind, pattern in DECLARATIONS:
        for match in pattern.finditer(text):
            name = match.group(1)
            if not name:
                continue
            symbols.append({'name': name, 'kind': kind,
                            'line': text.count('\n', 0, match.start()) + 1})
            if len(symbols) >= MAX_SYMBOLS:
                return symbols
    symbols.sort(key=lambda symbol: (symbol['line'], symbol['name']))
    return symbols[:MAX_SYMBOLS]


def task_terms(spec):
    """Return the terms of a task that a file can be relevant by."""
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
    for field in ('implementation', 'checks'):
        argv = spec.get(field)
        if isinstance(argv, list):
            for argument in argv:
                if isinstance(argument, str):
                    terms.update(WORD.findall(argument.casefold()))
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
                'files': [], 'selected': [], 'file_count': 0}
    files, truncated, problem = scan(workspace)
    if problem:
        return {'version': 1, 'assembled': False, 'reason': problem, 'files': [],
                'selected': [], 'file_count': 0}
    if not files:
        return {'version': 1, 'assembled': False, 'reason': 'the workspace holds no readable file',
                'files': [], 'selected': [], 'file_count': 0}
    root = Path(workspace).resolve()
    terms = task_terms(spec)
    named = named_files(spec, workspace)
    selected = select(files, terms, named, root)
    detailed = []
    for entry in selected:
        item = dict(entry)
        found = structure(root / entry['path'])
        item['symbols'] = found['symbols']
        item['structure_kind'] = found['kind']
        if found.get('reason'):
            item['structure_reason'] = found['reason']
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
        'limits': {'max_files': MAX_FILES, 'max_depth': MAX_DEPTH,
                   'max_file_bytes': MAX_FILE_BYTES, 'max_selected': MAX_SELECTED,
                   'max_symbols': MAX_SYMBOLS},
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
