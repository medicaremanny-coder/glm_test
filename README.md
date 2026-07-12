# glm_test

Python utilities generated and verified with the [GLM CLI](https://www.npmjs.com/package/glm-coding) — an AI code generator powered by Z.ai's GLM models.

## Contents

| File | Description |
|---|---|
| `url_shortener.py` | `URLShortener` class — hash-based URL shortener with collision handling |
| `test_url_shortener.py` | 37-test suite for `URLShortener` |
| `calculate_sum.py` | `calculate_sum` function — typed, validated numeric list summation |
| `test_calculate_sum.py` | Assertions + doctests for `calculate_sum` |

---

## URLShortener

A pure-Python, in-memory URL shortener. Uses SHA-256 hashing to generate short codes with automatic collision resolution and optional file-based persistence.

### Requirements

- Python 3.8+
- No third-party dependencies (stdlib only: `hashlib`, `base64`, `pathlib`, `logging`)

### Quick start

```python
from url_shortener import URLShortener

shortener = URLShortener()                          # default code_length=6
code = shortener.shorten_url('https://example.com/very/long/path')
print(code)                                         # e.g. "aB3xYz"

original = shortener.expand_url(code)
print(original)                                     # 'https://example.com/very/long/path'
```

### Constructor

```python
URLShortener(code_length: int = 6)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `code_length` | `int` | `6` | Length of generated codes. Must be between **4** and **12** inclusive. |

Raises `TypeError` if `code_length` is not an integer, `ValueError` if out of range.

### Methods

#### `shorten_url(url: str) -> str`

Shortens a URL and returns its short code. Calling with the same URL twice always returns the same code.

```python
code = shortener.shorten_url('https://github.com/user/repo')
```

- Accepts `http://` and `https://` URLs only.
- Raises `TypeError` for non-string input, `ValueError` for empty/whitespace or invalid protocol.

#### `expand_url(code: str) -> Optional[str]`

Returns the original URL for a given code, or `None` if the code is unknown.

```python
url = shortener.expand_url('aB3xYz')   # returns URL or None
```

#### `get_stats() -> Dict[str, int]`

Returns a snapshot of current state.

```python
stats = shortener.get_stats()
# {'total_urls': 3, 'total_codes': 3, 'code_length': 6}
```

#### `clear() -> None`

Removes all stored URL/code mappings.

```python
shortener.clear()
```

#### `save_to_file(file_path: str) -> None`

Persists all mappings to a CSV-style text file (`code,url` per line).

```python
shortener.save_to_file('/tmp/urls.txt')
```

Raises `FileNotFoundError` if the parent directory does not exist, `IOError` on write failure.

#### `load_from_file(file_path: str) -> None`

Loads mappings from a file previously written by `save_to_file`. Merges into existing state.

```python
shortener.load_from_file('/tmp/urls.txt')
```

Raises `FileNotFoundError` if the file does not exist, `ValueError` on invalid format.

### Collision handling

When two different URLs hash to the same base code, `_resolve_collision` appends a zero-padded counter suffix (e.g. `aB3x01`, `aB3x02`, …) until a unique code is found. Up to 999 attempts are made before a `RuntimeError` is raised.

### Limitations

- **Not thread-safe.** Use an external lock (e.g. `threading.Lock`) for concurrent access.
- **In-memory only** unless `save_to_file` / `load_from_file` are used.
- Codes are not guaranteed to be stable across Python versions (SHA-256 output is stable, but this is worth noting for long-term persistence).

### Running the demo

```bash
python3 url_shortener.py
```

---

## calculate_sum

A typed utility function that sums a list of integers or floats with full input validation.

```python
from calculate_sum import calculate_sum

calculate_sum([1, 2, 3, 4, 5])   # 15
calculate_sum([1.5, 2.5, 3.0])   # 7.0
calculate_sum([])                 # 0
```

Raises `TypeError` for non-list input or non-numeric elements, `ValueError` for `None`.

---

## Running the tests

No test framework installation required — uses the stdlib `unittest` module.

```bash
# URLShortener tests (37 tests)
python3 -m unittest test_url_shortener -v

# calculate_sum tests + doctests
python3 test_calculate_sum.py
```

---

## How the code was generated

All source files were generated using the [GLM CLI](https://www.npmjs.com/package/glm-coding):

```bash
glm -q "create a URL shortener class in Python with collision handling" -l python
glm -q "create a python function that takes a list of numbers and returns the sum" -l python
```

The test suites were written by hand to verify correctness of the generated code before committing.
