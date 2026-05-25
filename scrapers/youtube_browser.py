"""
YouTube チャンネルの「メールアドレスを表示」ボタンをブラウザ操作で取得する。
Claude Code の Claude-in-Chrome MCP ツールを使って呼び出す。

使い方（Claude Code セッション内から直接呼ぶ）:
    from scrapers.youtube_browser import fetch_youtube_email_instructions
    instructions = fetch_youtube_email_instructions("https://www.youtube.com/@example/about")
"""


def to_about_url(yt_url: str) -> str:
    """YouTube URL を /about URL に変換。チャンネルURLでなければ空文字を返す"""
    url = yt_url.split("?")[0].rstrip("/")
    if any(x in url for x in ["/watch", "playlist", "/shorts/", "/videos/"]):
        return ""
    if "/about" not in url:
        url += "/about"
    return url


def get_channel_handle(yt_url: str) -> str:
    """YouTube URL からチャンネルハンドル or ID を抽出"""
    import re
    m = re.search(r"youtube\.com/(@[^/]+|channel/[^/]+|c/[^/]+|user/[^/]+)", yt_url)
    return m.group(1) if m else ""


# ブラウザ操作の手順（Claude Code が MCP ツールで実行する際の参考）
BROWSER_STEPS = """
1. navigate: {about_url}
2. wait 2秒（ページ読み込み）
3. javascript: document.querySelector('button[aria-label*="説明"], #channel-description-container button')?.click()
   または find: "さらに表示" ボタンをクリック（チャンネル説明を展開）
4. wait 1秒
5. find: "メールアドレスを表示" ボタンを探す
   - あれば → クリック → bot認証があれば対応 → メールアドレスを取得
   - なければ → スキップ（このチャンネルはメール非公開）
6. javascript でメールを抽出:
   document.querySelector('yt-formatted-string[class*="email"]')?.textContent
   または EMAIL_RE でページ内を検索
"""
