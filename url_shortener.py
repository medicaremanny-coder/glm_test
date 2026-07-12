import os
import logging
from typing import Optional, Dict
from pathlib import Path
import hashlib
import base64


logger = logging.getLogger(__name__)


class URLShortener:
    """URL shortener service with collision handling.

    This class provides URL shortening functionality with automatic collision
    detection and resolution using counter suffixes.

    Attributes:
        url_to_code (Dict[str, str]): Maps long URLs to short codes
        code_to_url (Dict[str, str]): Maps short codes to long URLs
        code_length (int): Length of generated short codes

    Example:
        >>> shortener = URLShortener()
        >>> code = shortener.shorten_url('https://example.com')
        >>> original = shortener.expand_url(code)
        >>> assert original == 'https://example.com'

    Note:
        This implementation is not thread-safe. Use locking for concurrent access.
    """

    def __init__(self, code_length: int = 6) -> None:
        if not isinstance(code_length, int):
            raise TypeError(
                f"code_length must be integer, got {type(code_length).__name__}"
            )

        if not 4 <= code_length <= 12:
            raise ValueError(
                f"code_length must be between 4 and 12, got {code_length}"
            )

        self.url_to_code: Dict[str, str] = {}
        self.code_to_url: Dict[str, str] = {}
        self.code_length = code_length

    def _validate_url(self, url: str) -> None:
        if not isinstance(url, str):
            raise TypeError(
                f"URL must be string, got {type(url).__name__}"
            )

        if not url or not url.strip():
            raise ValueError("URL cannot be empty or whitespace")

        if not url.startswith(('http://', 'https://')):
            raise ValueError(
                f"Invalid URL protocol. Expected HTTP/HTTPS, got: {url}"
            )

    def _generate_base_code(self, url: str) -> str:
        url_bytes = url.encode('utf-8')
        hash_bytes = hashlib.sha256(url_bytes).digest()
        encoded = base64.urlsafe_b64encode(hash_bytes).decode('utf-8')
        return encoded[:self.code_length]

    def _resolve_collision(self, base_code: str, url: str) -> str:
        attempt = 1
        while attempt < 1000:
            code = base_code[:max(1, self.code_length - 2)] + str(attempt).zfill(2)
            if code not in self.code_to_url:
                return code
            attempt += 1

        raise RuntimeError(
            f"Failed to generate unique code after {attempt} attempts for URL: {url}"
        )

    def shorten_url(self, url: str) -> str:
        self._validate_url(url)

        if url in self.url_to_code:
            logger.debug(f"URL already shortened: {url} -> {self.url_to_code[url]}")
            return self.url_to_code[url]

        base_code = self._generate_base_code(url)

        if base_code in self.code_to_url:
            if self.code_to_url[base_code] == url:
                return base_code
            logger.info(f"Collision detected for code {base_code}, resolving...")
            final_code = self._resolve_collision(base_code, url)
        else:
            final_code = base_code

        self.url_to_code[url] = final_code
        self.code_to_url[final_code] = url

        logger.info(f"Shortened URL: {url} -> {final_code}")
        return final_code

    def expand_url(self, code: str) -> Optional[str]:
        if not isinstance(code, str):
            raise TypeError(
                f"Code must be string, got {type(code).__name__}"
            )

        if not code or not code.strip():
            raise ValueError("Code cannot be empty or whitespace")

        url = self.code_to_url.get(code)

        if url:
            logger.debug(f"Expanded code: {code} -> {url}")
        else:
            logger.warning(f"Code not found: {code}")

        return url

    def save_to_file(self, file_path: str) -> None:
        if not isinstance(file_path, str):
            raise TypeError(
                f"file_path must be string, got {type(file_path).__name__}"
            )

        if not file_path or not file_path.strip():
            raise ValueError("file_path cannot be empty or whitespace")

        path = Path(file_path)

        if path.parent != Path('.') and not path.parent.exists():
            raise FileNotFoundError(
                f"Directory does not exist: {path.parent}"
            )

        try:
            with path.open('w', encoding='utf-8') as f:
                for url, code in self.url_to_code.items():
                    f.write(f"{code},{url}\n")
            logger.info(f"Saved {len(self.url_to_code)} mappings to {file_path}")
        except IOError as e:
            raise IOError(
                f"Failed to write to file {file_path}: {e}"
            ) from e

    def load_from_file(self, file_path: str) -> None:
        if not isinstance(file_path, str):
            raise TypeError(
                f"file_path must be string, got {type(file_path).__name__}"
            )

        if not file_path or not file_path.strip():
            raise ValueError("file_path cannot be empty or whitespace")

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        try:
            with path.open('r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    parts = line.split(',', 1)
                    if len(parts) != 2:
                        raise ValueError(
                            f"Invalid format at line {line_num}: {line}"
                        )

                    code, url = parts
                    self._validate_url(url)

                    self.code_to_url[code] = url
                    self.url_to_code[url] = code

            logger.info(
                f"Loaded {len(self.url_to_code)} mappings from {file_path}"
            )
        except IOError as e:
            raise IOError(
                f"Failed to read file {file_path}: {e}"
            ) from e
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"Invalid file format in {file_path}: {e}"
            ) from e

    def get_stats(self) -> Dict[str, int]:
        return {
            'total_urls': len(self.url_to_code),
            'total_codes': len(self.code_to_url),
            'code_length': self.code_length,
        }

    def clear(self) -> None:
        self.url_to_code.clear()
        self.code_to_url.clear()
        logger.info("Cleared all URL mappings")


def main() -> None:
    """Demonstrate URL shortener usage."""
    logging.basicConfig(level=logging.INFO)

    shortener = URLShortener(code_length=6)

    urls = [
        'https://example.com',
        'https://github.com/user/repo',
        'https://docs.python.org/3/library/pathlib.html',
    ]

    codes = []
    for url in urls:
        try:
            code = shortener.shorten_url(url)
            codes.append(code)
            print(f"{url} -> {code}")
        except (ValueError, TypeError, RuntimeError) as e:
            print(f"Error shortening {url}: {e}")

    print("\nExpanding codes:")
    for code in codes:
        try:
            original = shortener.expand_url(code)
            print(f"{code} -> {original}")
        except (ValueError, TypeError) as e:
            print(f"Error expanding {code}: {e}")

    stats = shortener.get_stats()
    print(f"\nStats: {stats}")

    temp_dir = Path.home() / '.url_shortener'
    temp_dir.mkdir(exist_ok=True)
    data_file = temp_dir / 'urls.txt'

    try:
        shortener.save_to_file(str(data_file))
        print(f"\nSaved to: {data_file}")

        new_shortener = URLShortener()
        new_shortener.load_from_file(str(data_file))
        print(f"Loaded {new_shortener.get_stats()['total_urls']} URLs")
    except (IOError, ValueError, FileNotFoundError) as e:
        print(f"File operation error: {e}")


if __name__ == '__main__':
    main()
