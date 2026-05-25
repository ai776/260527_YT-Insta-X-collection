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
           "note.com", "lit.link", "inquir", "contact", "/form", "/inquiry")

BLOG_DOMAINS = ["ameblo.jp", "note.com", "hatenablog.com", "livedoor.blog",
                "fc2.com/blog", "jugem.jp", "seesaa.net", "blog.jp"]


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
    # パスが浅い（プロフィール本体）ものを優先
    for url in candidates:
        if any(d in url for d in domains):
            path = url.split("/", 3)[-1] if url.count("/") >= 3 else ""
            # 投稿・動画・プレイリストURLを除外
            if not any(x in url for x in ["/status/", "/watch?", "playlist?", "/videos/", "/posts/", "/p/"]):
                return url
    # なければ最初のヒット
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
    """ブログURL を検索（ameba・note・はてなブログ等）"""
    if record.blog_url:
        return record
    query = f'{record.name} {record.company} ブログ'
    try:
        items = _search(query, num=5)
        for item in items:
            url = item.get("link", "")
            if any(d in url for d in BLOG_DOMAINS):
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
    query = f'{record.name} {record.company} メールアドレス contact email'
    try:
        items = _search(query, num=5)
        import re
        EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
        FAKE = (".png", ".jpg", ".gif", ".woff", ".svg", "example.com", "sentry.io")
        for item in items:
            # スニペット内からメールを探す
            snippet = item.get("snippet", "") + item.get("link", "")
            for em in EMAIL_RE.findall(snippet):
                if not any(f in em for f in FAKE):
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

    # クエリを複数試して最初にヒットした公式っぽいURLを使う
    queries = [
        f'{record.name} {record.company} 公式サイト',
        f'{record.name} {record.company} オフィシャルサイト',
        f'{record.name} {record.company} 会社概要',
    ]
    try:
        for query in queries:
            items = _search(query, num=5)
            for item in items:
                url = item.get("link", "")
                if not any(s in url for s in SKIP_HP):
                    record.company_hp = url
                    break
            if record.company_hp:
                break
            time.sleep(delay)
    except Exception as e:
        record.notes += f"[HP検索エラー: {e}] "
    time.sleep(delay)
    return record
