"""Serper.dev を使って SNS URL を検索する（無料2,500件/月）"""
import os
import time
import requests
from models import PersonRecord

SERPER_ENDPOINT = "https://google.serper.dev/search"

SNS_SITES = [
    ("x_url",        ["x.com", "twitter.com"]),
    ("facebook_url", ["facebook.com"]),
    ("youtube_url",  ["youtube.com"]),
    ("instagram_url",["instagram.com"]),
]

SKIP_HP = ("x.com", "twitter.com", "facebook.com", "youtube.com",
           "instagram.com", "amazon.co.jp", "wikipedia.org", "ameblo.jp",
           "note.com", "lit.link", "linktr.ee", "tiktok.com", "threads.net",
           "threads.com", "lin.ee", "linktree", "potofu.me", "profcard.info",
           "inquir", "contact", "/form", "/inquiry")

BLOG_DOMAINS = ["ameblo.jp", "note.com", "hatenablog.com", "livedoor.blog",
                "fc2.com/blog", "jugem.jp", "seesaa.net", "blog.jp"]

# 単一記事ページを示唆するパス（プロフィール/トップではない）
BLOG_ARTICLE_PATTERNS = ("/entry-", "/entry/", "/n/", "/p/", "/posts/",
                          "/archive/", "/article/", "?p=")


def _api_key() -> str:
    key = os.environ.get("SERPER_KEY")
    if not key:
        raise ValueError("SERPER_KEY が環境変数に設定されていません")
    return key


def _search(query: str, num: int = 5) -> list[dict]:
    resp = requests.post(
        SERPER_ENDPOINT,
        headers={"X-API-KEY": _api_key(), "Content-Type": "application/json"},
        json={"q": query, "num": num, "hl": "ja", "gl": "jp"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("organic", [])


def _best_profile_url(items: list[dict], domains: list[str]) -> str:
    """プロフィールページらしいURLを優先して返す"""
    candidates = [item.get("link", "") for item in items]
    # 除外パターン（投稿・動画・非公式ページ）
    EXCLUDE = ["/status/", "/watch?", "playlist?", "/videos/", "/posts/", "/p/",
               "facebook.com/pages/"]  # Facebook非公式ページ（/pages/{名前}/{ID}形式）を除外
    # パスが浅い公式プロフィールを優先
    for url in candidates:
        if any(d in url for d in domains):
            if not any(x in url for x in EXCLUDE):
                return url
    # 除外パターンに引っかかったものをフォールバックとして返す
    for url in candidates:
        if any(d in url for d in domains):
            return url
    return ""


def search_sns(record: PersonRecord, delay: float = 1.0) -> PersonRecord:
    """SNSごとに個別検索して取得精度を上げる"""
    for field, domains in SNS_SITES:
        if getattr(record, field):
            continue
        query = f'{record.name} {record.company} site:{domains[0]}'
        try:
            items = _search(query, num=5)
            url = _best_profile_url(items, domains)
            if url:
                setattr(record, field, url)
        except Exception as e:
            record.notes += f"[{field}検索エラー: {e}] "
        time.sleep(delay)
    return record


def search_blog(record: PersonRecord, delay: float = 1.0) -> PersonRecord:
    """ブログURL を検索（プロフィール/トップページのみ、記事ページは除外）"""
    if record.blog_url:
        return record
    hint = f' {record.handle}' if record.handle else ''
    query = f'{record.name} {record.company}{hint} ブログ'
    try:
        items = _search(query, num=8)
        # 第1優先: プロフィール/トップページ (記事URLパターンを除外)
        for item in items:
            url = item.get("link", "")
            if not any(d in url for d in BLOG_DOMAINS):
                continue
            if any(p in url for p in BLOG_ARTICLE_PATTERNS):
                continue
            record.blog_url = url
            break
    except Exception as e:
        record.notes += f"[ブログ検索エラー: {e}] "
    time.sleep(delay)
    return record


def search_email(record: PersonRecord, delay: float = 1.0) -> PersonRecord:
    """メールアドレスを直接検索する"""
    if record.email:
        return record
    hint = f' {record.handle}' if record.handle else ''
    query = f'{record.name} {record.company}{hint} メールアドレス contact email'
    # HPドメインを取得（採用判定で使用）
    hp_domain = ""
    if record.company_hp:
        from urllib.parse import urlparse
        try:
            hp_domain = urlparse(record.company_hp).netloc.lower().lstrip("www.")
        except Exception:
            hp_domain = ""
    try:
        items = _search(query, num=5)
        import re
        EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
        FAKE = (".png", ".jpg", ".gif", ".woff", ".svg", "example.com", "sentry.io")
        # 大手企業ドメイン（同名別人由来の混入をブロック）
        CORP_BLOCK = ("smbc-card.com", "mufg.jp", "rakuten.co.jp", "amazon.co.jp",
                       "yahoo.co.jp", "google.com", "apple.com", "microsoft.com",
                       "softbank.jp", "ntt.co.jp", "kddi.com", "docomo.ne.jp",
                       "jp.com", "jal.co.jp", "ana.co.jp", "info@info.")
        for item in items:
            snippet = item.get("snippet", "") + " " + item.get("link", "")
            for em in EMAIL_RE.findall(snippet):
                em_lower = em.lower()
                tld = em.rsplit(".", 1)[-1].lower()
                bad_tld = tld in ("http", "https", "html", "php", "asp", "aspx", "www")
                if any(f in em_lower for f in FAKE): continue
                if any(c in em_lower for c in CORP_BLOCK): continue
                if not (2 <= len(tld) <= 6) or bad_tld: continue
                # HPドメインが既知の場合は一致するもののみ採用
                em_domain = em_lower.split("@", 1)[1] if "@" in em_lower else ""
                if hp_domain and em_domain and hp_domain not in em_domain and em_domain not in hp_domain:
                    continue
                record.email = em
                return record
    except Exception as e:
        record.notes += f"[メール検索エラー: {e}] "
    time.sleep(delay)
    return record


def search_hp(record: PersonRecord, delay: float = 1.0) -> PersonRecord:
    """会社HP・公式サイトを検索"""
    if record.company_hp:
        return record

    # ハンドル名併用で本人特定強化（SNS表示名は芸名のため）
    hint = f' {record.handle}' if record.handle else ''
    queries = [
        f'{record.name}{hint} 公式サイト',
        f'{record.name}{hint} オフィシャルサイト',
        f'{record.name} {record.company} 会社概要',
    ]
    # 第三者メディア/EC等を除外（インフルエンサーは記事/販売ページが上位ヒットしやすい）
    THIRD_PARTY = ("cosme.net", "kadokawa", "shogakukan", "shueisha",
                    "store.", "shop.", "/feature/", "/interview/",
                    "/article/", "/products/", "prtimes.jp", "natalie.mu",
                    "modelpress.com", "oricon.co.jp", "/news/")
    handle_keys = [k.lower() for k in [record.handle or ""] if k]
    try:
        for query in queries:
            items = _search(query, num=8)
            for item in items:
                url = item.get("link", "").lower()
                if not url: continue
                if any(s in url for s in SKIP_HP): continue
                if any(s in url for s in THIRD_PARTY): continue
                # ハンドル名が含まれていれば本人HPの可能性が高い
                if handle_keys and not any(k in url for k in handle_keys):
                    continue
                record.company_hp = item.get("link", "")
                break
            if record.company_hp:
                break
            time.sleep(delay)
    except Exception as e:
        record.notes += f"[HP検索エラー: {e}] "
    time.sleep(delay)
    return record
