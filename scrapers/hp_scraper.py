"""会社HP・プロフィールページからメール・問い合わせフォームを抽出"""
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from models import PersonRecord

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
TIMEOUT = 10
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
CONTACT_KEYWORDS = ["contact", "お問い合わせ", "問い合わせ", "inquiry", "form", "メール"]
FAKE_EMAIL_EXTS = (".png", ".jpg", ".gif", ".woff", ".svg", ".webp", ".css", ".js")
FAKE_EMAIL_DOMAINS = ("sentry.io", "example.com", "yourdomain", "domain.com",
                      "wixpress.com", "squarespace.com", "amazonaws.com")


def _fetch(url: str) -> BeautifulSoup | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except Exception:
        return None


def _is_real_email(em: str) -> bool:
    if any(em.endswith(ext) for ext in FAKE_EMAIL_EXTS):
        return False
    if any(d in em for d in FAKE_EMAIL_DOMAINS):
        return False
    # TLD が短すぎる or 長すぎる（正規ドメインは2〜6文字）
    tld = em.rsplit(".", 1)[-1].lower()
    if not (2 <= len(tld) <= 6):
        return False
    # プロトコル名・URLパーツが混入しているケースを除外
    if tld in ("http", "https", "html", "php", "asp", "aspx", "www"):
        return False
    return True


def _find_email(soup: BeautifulSoup) -> str:
    # mailto: リンクを最優先
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("mailto:"):
            em = href.replace("mailto:", "").split("?")[0].strip()
            if _is_real_email(em):
                return em
    # HTMLソース全体から正規表現で探す（JS内に埋まっているケースも拾う）
    raw = str(soup)
    for em in EMAIL_RE.findall(raw):
        if _is_real_email(em):
            return em
    return ""


URL_CONTACT_KEYWORDS = ["inquir", "contact", "お問い合わせ", "inquiry"]
URL_EXCLUDE_KEYWORDS = ["performance", "platform", "reform", "inform", "uniform"]
TEXT_CONTACT_KEYWORDS = ["お問い合わせ", "問い合わせ", "contact", "inquiry", "メール"]


def _find_contact_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    """問い合わせページのURLを集める。URLパスに含むものを優先。"""
    url_match = []
    text_match = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("http"):
            full = href.split("#")[0]
        elif href.startswith("/"):
            parsed = urlparse(base_url)
            full = f"{parsed.scheme}://{parsed.netloc}{href.split('#')[0]}"
        else:
            continue
        if (any(kw in full.lower() for kw in URL_CONTACT_KEYWORDS)
                and not any(ex in full.lower() for ex in URL_EXCLUDE_KEYWORDS)):
            url_match.append(full)
        elif any(kw in a.get_text().lower() for kw in TEXT_CONTACT_KEYWORDS):
            text_match.append(full)
    # URLパスに含むものを優先、なければリンクテキスト一致
    return url_match + text_match


def scrape_hp(record: PersonRecord) -> PersonRecord:
    if not record.company_hp:
        return record

    soup = _fetch(record.company_hp)
    if not soup:
        return record

    # HPトップでメール探索
    if not record.email:
        record.email = _find_email(soup)

    # 問い合わせリンクを収集
    contact_links = _find_contact_links(soup, record.company_hp)
    if contact_links and not record.contact_form_url:
        record.contact_form_url = contact_links[0]

    # 問い合わせ・概要ページを順番に見てメールを探す
    if not record.email:
        for link in contact_links[:3]:
            sub_soup = _fetch(link)
            if sub_soup:
                record.email = _find_email(sub_soup)
                if record.email:
                    break

    return record
