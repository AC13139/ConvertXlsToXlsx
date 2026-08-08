# API Reference

The package exposes a small, stable surface. Anything not listed here is
considered private and may change without notice.

## `convertxls.convert_file`

```python
convert_file(src, dst=None, *, backend="auto", overwrite=False, verbose=False) -> ConversionResult
```

Convert a single `.xls` file into a `.xlsx` file.

| Parameter  | Type | Default | Description |
|------------|------|---------|-------------|
| `src`      | `str \| Path` | — | Path to the input `.xls` file. |
| `dst`      | `str \| Path \| None` | `None` | Output path. When `None`, the result is written next to `src` as `<stem>.xlsx`. |
| `backend`  | `str` | `"auto"` | Backend name (currently only `"libreoffice"` is shipped). |
| `overwrite`| `bool`| `False` | When `False` and `dst` exists, raise `InvalidPathError`. |
| `verbose`  | `bool`| `False` | Emit debug logs. |

Returns a `ConversionResult`. Raises `ConvertXlsError` subclasses on
failure.

## `convertxls.convert_many`

```python
convert_many(files, *, out_dir, backend="auto", overwrite=False, workers=4, verbose=False) -> list[ConversionResult]
```

Convert an explicit list of `.xls` files into a single output directory.
Stems are preserved; collisions raise `InvalidPathError` unless
`overwrite=True`.

| Parameter   | Type | Default | Description |
|-------------|------|---------|-------------|
| `files`     | `Sequence[str \| Path]` | — | Input files. |
| `out_dir`   | `str \| Path` | — | Destination directory. Created if missing. |
| `backend`   | `str` | `"auto"` | Backend name or `"auto"`. |
| `overwrite` | `bool` | `False` | Overwrite existing outputs. |
| `workers`   | `int` | `4` | Parallel workers (1 = sequential). |
| `verbose`   | `bool` | `False` | Emit debug logs. |

Returns a `list[ConversionResult]`. An empty input returns an empty list
without contacting any backend.

## `convertxls.convert_directory`

```python
convert_directory(src_dir, dst_dir=None, *, backend="auto", overwrite=False, workers=4, verbose=False) -> list[ConversionResult]
```

Recursively convert every `.xls` file under `src_dir`.

When `dst_dir` is `None`, each output is written next to its source.
Otherwise, the directory tree under `src_dir` is mirrored under
`dst_dir/<src_folder_name>/` — the source folder's basename is preserved
as the top-level directory (rsync convention).

| Parameter   | Type | Default | Description |
|-------------|------|---------|-------------|
| `src_dir`   | `str \| Path` | — | Source directory. |
| `dst_dir`   | `str \| Path \| None` | `None` | Destination directory (in-place if `None`). |
| `backend`   | `str` | `"auto"` | Backend name or `"auto"`. |
| `overwrite` | `bool` | `False` | Overwrite existing outputs. |
| `workers`   | `int` | `4` | Parallel workers (1 = sequential). |
| `verbose`   | `bool` | `False` | Emit debug logs. |

Returns a `list[ConversionResult]`.

## `convertxls.list_backends`

```python
list_backends() -> list[str]
```

Return the names of every registered backend in priority order.

## `convertxls.available_backends`

```python
available_backends() -> list[Converter]
```

Return the registered backends whose binary is on `PATH`. As of 0.1.x
the only registered backend is `libreoffice`.

## `convertxls.discover_xls_files`

```python
discover_xls_files(src_dir) -> DiscoveryResult
```

Walk `src_dir` and return every `.xls` file. Symlinks are not followed;
results are lex-sorted.

## Data classes

### `convertxls.converters.ConversionResult`

```python
@dataclass(frozen=True)
class ConversionResult:
    src: Path
    dst: Path
    backend: str
    duration_ms: int
    return_code: int
    stdout: str = ""
    stderr: str = ""
```

`result.ok` returns `True` iff `return_code == 0`.

### `convertxls.converters.BackendInfo`

```python
@dataclass(frozen=True)
class BackendInfo:
    name: str
    priority: int
    available: bool
```

### `convertxls.config.ConversionOptions`

```python
@dataclass(frozen=True)
class ConversionOptions:
    backend: str = "auto"
    overwrite: bool = False
    workers: int = 4
    verbose: bool = False
```

### `convertxls.config.DiscoveryResult`

```python
@dataclass(frozen=True)
class DiscoveryResult:
    src_dir: str
    files: tuple[tuple[str, str], ...] = ()
```

Each `files` entry is `(absolute_path, relative_to_src_dir)`.

## Exceptions

All inherit from `ConvertXlsError`:

| Class | Cause |
|-------|-------|
| `ConverterNotFoundError` | A named backend was requested but not registered. |
| `NoConverterAvailableError` | No backend is registered *and* installed. |
| `ConversionFailedError` | A backend ran but the conversion failed (carries `backend`, `src`, `return_code`, `stderr`). |
| `InvalidPathError` | A caller-supplied path was invalid. |
