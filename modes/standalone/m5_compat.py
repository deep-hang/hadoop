"""Explicit host I/O paths and owned, short Windows Docker input snapshots."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import sys
import tempfile


def plain_path(value):
    text = os.fspath(value)
    if os.name == 'nt':
        if text.startswith('\\\\?\\UNC\\'):
            text = '\\\\' + text[8:]
        elif text.startswith('\\\\?\\'):
            text = text[4:]
    return Path(text)


def fs_path(value):
    path = plain_path(value)
    if os.name != 'nt':
        return path
    text = os.path.abspath(path)
    return Path('\\\\?\\UNC\\' + text[2:] if text.startswith('\\\\') else '\\\\?\\' + text)


def plain_paths(values):
    return (plain_path(value) for value in values)


def secondary_error(original, label, error):
    message = label + ': ' + str(error)
    if original is not None:
        try:
            original.secondary_errors = [*getattr(original, 'secondary_errors', []), message]
        except (AttributeError, TypeError):
            pass
    print(message, file=sys.stderr, flush=True)


def input_manifest(folder):
    rows = []
    for path in sorted(plain_paths(fs_path(folder).iterdir()), key=lambda p: p.name):
        if path.name.startswith(('.', '_')):
            continue
        if fs_path(path).is_symlink() or not fs_path(path).is_file():
            raise ValueError('Temporary input requires ordinary files: ' + str(path))
        digest = hashlib.sha256()
        with fs_path(path).open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block)
        rows.append(dict(name=path.name, bytes=fs_path(path).stat().st_size, sha256=digest.hexdigest()))
    return rows


class StagedInput:
    def __init__(self, source, repository, token):
        self.source = plain_path(source)
        self.repository = str(plain_path(repository).absolute())
        self.token = token
        parent = plain_path(os.environ.get('M5_TEMP_DIR') or tempfile.gettempdir())
        fs_path(parent).mkdir(parents=True, exist_ok=True)
        self.directory = plain_path(tempfile.mkdtemp(prefix='m5-', dir=fs_path(parent)))
        self.path = self.directory / 'input'
        self.owner = dict(repository=self.repository, token=token, directory=str(self.directory))
        try:
            fs_path(self.directory / 'owner.json').write_text(json.dumps(self.owner), encoding='utf-8')
            fs_path(self.path).mkdir()
            before = input_manifest(source)
            if not before:
                raise ValueError('Input snapshot has no ordinary files')
            for row in before:
                shutil.copyfile(fs_path(self.source / row['name']), fs_path(self.path / row['name']))
            if before != input_manifest(source) or before != input_manifest(self.path):
                raise RuntimeError('Input changed while preparing Docker snapshot')
        except BaseException as original:
            try:
                # This directory was exclusively allocated in this constructor;
                # creation can fail before owner.json itself has been written.
                shutil.rmtree(fs_path(self.directory))
            except Exception as error:
                secondary_error(original, 'Temporary input cleanup failed', error)
            raise


def cleanup_staging(owner, repository, token):
    if not owner:
        return
    folder = plain_path(owner['directory'])
    expected = dict(repository=str(plain_path(repository).absolute()), token=token, directory=str(folder))
    if owner != expected or not folder.name.startswith('m5-'):
        raise RuntimeError('Temporary input ownership mismatch')
    if not fs_path(folder).exists():
        return
    if fs_path(folder).is_symlink():
        raise RuntimeError('Refusing temporary input symlink')
    actual = json.loads(fs_path(folder / 'owner.json').read_text(encoding='utf-8'))
    if actual != expected:
        raise RuntimeError('Temporary input owner file mismatch')
    # Python 3.10 supports removing trees using an extended Windows path.
    shutil.rmtree(fs_path(folder))
