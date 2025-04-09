"""
Type stubs for Django components used in the ChessMate application.

This module provides type hints for Django components that don't have proper type stubs.
It helps to satisfy mypy type checking requirements.
"""

from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast


# Django cache type stubs
class BaseCache:
    """Base cache stub for Django's cache backend."""

    def get(self, key: str, default: Any = None) -> Any: ...
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> None: ...
    def add(self, key: str, value: Any, timeout: Optional[int] = None) -> bool: ...
    def delete(self, key: str) -> None: ...
    def get_many(self, keys: List[str]) -> Dict[str, Any]: ...
    def set_many(self, data: Dict[str, Any], timeout: Optional[int] = None) -> None: ...
    def delete_many(self, keys: List[str]) -> None: ...
    def clear(self) -> None: ...
    def incr(self, key: str, delta: int = 1) -> int: ...
    def decr(self, key: str, delta: int = 1) -> int: ...
    def close(self) -> None: ...
    def touch(self, key: str, timeout: Optional[int] = None) -> bool: ...


# Django request/response type stubs
class HttpRequest:
    """Stub for Django's HttpRequest."""

    method: str
    GET: Dict[str, Any]
    POST: Dict[str, Any]
    body: bytes
    META: Dict[str, Any]
    COOKIES: Dict[str, str]
    session: Dict[str, Any]
    user: Any
    headers: Dict[str, str]
    path: str
    path_info: str
    content_type: str

    def get_full_path(self) -> str: ...
    def get_host(self) -> str: ...
    def build_absolute_uri(self, location: Optional[str] = None) -> str: ...


class HttpResponse:
    """Stub for Django's HttpResponse."""

    content: bytes
    status_code: int
    cookies: Dict[str, Any]
    headers: Dict[str, str]

    def __init__(
        self, content: Any = b"", content_type: Optional[str] = None, status: int = 200, reason: Optional[str] = None
    ) -> None: ...
    def set_cookie(self, key: str, value: str = "", **kwargs: Any) -> None: ...
    def delete_cookie(self, key: str, **kwargs: Any) -> None: ...


# Django settings stub
class Settings:
    """Stub for Django settings."""

    DEBUG: bool
    CACHES: Dict[str, Dict[str, Any]]
    CACHE_MIDDLEWARE_SECONDS: int
    SECRET_KEY: str
    ALLOWED_HOSTS: List[str]
    INSTALLED_APPS: List[str]
    MIDDLEWARE: List[str]
    DATABASES: Dict[str, Dict[str, Any]]
    REDIS_URL: str


# Django models stub
class Model:
    """Stub for Django models."""

    id: int
    pk: Any

    def save(self, *args: Any, **kwargs: Any) -> None: ...
    def delete(self, *args: Any, **kwargs: Any) -> None: ...

    @classmethod
    def objects(cls) -> Any: ...


# DRF Response stub
class Response(HttpResponse):
    """Stub for DRF Response."""

    data: Any

    def __init__(
        self,
        data: Any = None,
        status: int = 200,
        template_name: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        exception: bool = False,
        content_type: Optional[str] = None,
    ) -> None: ...
