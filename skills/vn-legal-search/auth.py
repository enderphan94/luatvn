"""Đăng nhập luatvietnam.vn.

Flow thực tế (ASP.NET Core Antiforgery):
  1. GET /khach-hang/sso/authentication → set cookies + embed __RequestVerificationToken
  2. POST /khach-hang/api/v1/customer/login với form-encoded data + token
  3. Server set auth cookie. Lưu cookies → tái sử dụng cho mọi request sau.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

SKILL_DIR = Path(__file__).parent
load_dotenv(SKILL_DIR / ".env")

BASE = "https://luatvietnam.vn"
LOGIN_PAGE = f"{BASE}/khach-hang/sso/authentication?returnUrl=%2F"
LOGIN_API = f"{BASE}/khach-hang/api/v1/customer/login"
SESSION_CACHE = SKILL_DIR / "cache" / ".session"

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
)


def _credentials() -> tuple[str, str]:
    u = os.getenv("LUATVN_USERNAME")
    p = os.getenv("LUATVN_PASSWORD")
    if not u or not p:
        raise RuntimeError(
            "Thiếu credentials. Tạo file .env trong thư mục skill với:\n"
            "  LUATVN_USERNAME=email_của_bạn\n"
            "  LUATVN_PASSWORD=mật_khẩu"
        )
    return u, p


def _ttl_seconds() -> int:
    return int(os.getenv("LUATVN_SESSION_TTL", "3600"))


def get_session(verify_cached: bool = True) -> requests.Session:
    """Trả session đã đăng nhập. Tái sử dụng cache nếu còn fresh + verified.

    Args:
        verify_cached: nếu True, validate cached session bằng cách check homepage.
            Nếu cached cookies invalid (server đã hết hạn trước TTL), clear + re-login.
    """
    s = requests.Session()
    s.headers.update({"User-Agent": UA})

    cached = _load_cache()
    if cached and time.time() - cached["timestamp"] < _ttl_seconds():
        s.cookies.update(cached["cookies"])
        if not verify_cached or _is_session_valid(s):
            return s
        # Cached cookies hết hạn server-side → clear + re-login
        clear_cache()

    return _login(s)


def _is_session_valid(s: requests.Session) -> bool:
    """Quick check: GET homepage và tìm dấu hiệu đã login (logout link, username)."""
    try:
        r = s.get(BASE + "/", timeout=10)
        if r.status_code != 200:
            return False
        markers = ["dang-xuat", "logout", "Đăng xuất"]
        return any(m.lower() in r.text.lower() for m in markers)
    except requests.RequestException:
        return False


def _login(s: requests.Session) -> requests.Session:
    # Bước 1: GET trang login → cookies (Antiforgery, ASP.NET_SessionId) + token trong HTML
    r = s.get(LOGIN_PAGE, timeout=20)
    r.raise_for_status()

    token = _extract_antiforgery_token(r.text)
    if not token:
        raise RuntimeError(
            "Không tìm thấy __RequestVerificationToken trong HTML trang login. "
            "Có thể trang đã đổi cấu trúc."
        )

    user, pwd = _credentials()

    # Bước 2: POST login với form data
    form = {
        "CustomerName": user,
        "Password": pwd,
        "Remember": "true",
        "ReturnUrl": "/",
        "__RequestVerificationToken": token,
        "X-Requested-With": "XMLHttpRequest",
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": BASE,
        "Referer": LOGIN_PAGE,
        "Accept": "*/*",
    }
    r = s.post(LOGIN_API, data=form, headers=headers, timeout=20)

    if r.status_code != 200:
        raise RuntimeError(f"Login HTTP {r.status_code}: {r.text[:300]}")

    # Server có thể trả JSON {success: bool, ...} — kiểm tra nếu có
    try:
        body = r.json()
        if isinstance(body, dict):
            if body.get("success") is False or body.get("Success") is False:
                raise RuntimeError(f"Login thất bại: {body}")
    except ValueError:
        # Không phải JSON → có thể là HTML/redirect, vẫn ok nếu cookies set
        pass

    _save_cache({"timestamp": time.time(), "cookies": dict(s.cookies)})
    return s


_TOKEN_RE = re.compile(
    r'name="__RequestVerificationToken"[^>]*value="([^"]+)"'
)


def _extract_antiforgery_token(html: str) -> Optional[str]:
    m = _TOKEN_RE.search(html)
    return m.group(1) if m else None


def _load_cache() -> Optional[dict]:
    try:
        if SESSION_CACHE.exists():
            return json.loads(SESSION_CACHE.read_text())
    except Exception:
        pass
    return None


def _save_cache(data: dict) -> None:
    SESSION_CACHE.parent.mkdir(parents=True, exist_ok=True)
    SESSION_CACHE.write_text(json.dumps(data))


def clear_cache() -> None:
    if SESSION_CACHE.exists():
        SESSION_CACHE.unlink()


if __name__ == "__main__":
    sess = get_session()
    print("=== Cookies sau khi login ===")
    for k, v in sess.cookies.items():
        preview = v[:40] + "..." if len(v) > 40 else v
        print(f"  {k} = {preview}")

    # Verify: fetch trang chủ với session đã login
    r = sess.get(BASE + "/", timeout=15)
    print(f"\n=== Verify GET / ===")
    print(f"Status: {r.status_code}, body length: {len(r.text)}")

    # Tìm dấu hiệu đã đăng nhập (link logout, tên user, v.v.)
    indicators = ["dang-xuat", "logout", "Đăng xuất", "thaingocngan", "Tài khoản"]
    found = [w for w in indicators if w.lower() in r.text.lower()]
    if found:
        print(f"Login OK — phát hiện: {found}")
    else:
        print("⚠ Không tìm thấy dấu hiệu đã login trên trang chủ — kiểm tra lại")
