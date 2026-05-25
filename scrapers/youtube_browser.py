"""
YouTube チャンネル情報をブラウザ操作で取得するユーティリティ。
- get_channel_info(): 登録者数・メールアドレスをまとめて取得
- to_about_url(): YouTube URL を /about URL に変換
"""
import re

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
SUBSCRIBER_RE = re.compile(r"チャンネル登録者数\s*([\d.,万千億]+)")


def to_about_url(yt_url: str) -> str:
    """YouTube URL を /about URL に変換。チャンネルURLでなければ空文字を返す"""
    url = yt_url.split("?")[0].rstrip("/")
    if any(x in url for x in ["/watch", "playlist", "/shorts/", "/videos/"]):
        return ""
    if "/about" not in url:
        url += "/about"
    return url


def parse_subscribers(text: str) -> str:
    """ページテキストから登録者数を抽出（例: '5.6万'）"""
    m = SUBSCRIBER_RE.search(text)
    return m.group(1) if m else ""


def js_get_channel_info() -> str:
    """
    ブラウザで実行するJSコード。
    チャンネルの概要モーダルから登録者数・メールを取得する。
    使い方: mcp__claude-in-chrome__javascript_tool で実行
    """
    return """
(function() {
    const dialog = document.querySelector('tp-yt-paper-dialog, ytd-about-channel-renderer');
    if (!dialog) return {error: 'モーダルが開いていません'};
    const text = dialog.innerText || '';
    const subMatch = text.match(/チャンネル登録者数\\s*([\\d.,万千億]+)/);
    const emailMatch = text.match(/[a-zA-Z0-9._%+\\-]+@[a-zA-Z0-9.\\-]+\\.[a-zA-Z]{2,}/g);
    const fakeTld = ['https','http','html','php','asp','www'];
    const emails = (emailMatch || []).filter(e => {
        const tld = e.split('.').pop().toLowerCase();
        return tld.length >= 2 && tld.length <= 6 && !fakeTld.includes(tld);
    });
    return {
        subscribers: subMatch ? subMatch[1] : '',
        email: emails[0] || ''
    };
})()
"""
