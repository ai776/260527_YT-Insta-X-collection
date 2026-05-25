"""
X（Twitter）フォロワー数をブラウザ操作で取得するユーティリティ。
- js_get_followers(): フォロワー数取得JSコード文字列を返す
- to_x_url(): X プロフィールURLに正規化
"""
import re


def to_x_url(x_url: str) -> str:
    """X URL をプロフィールURLに正規化。プロフィール以外は空文字を返す"""
    url = x_url.split("?")[0].rstrip("/")
    if any(x in url for x in ["/status/", "/lists/", "/i/"]):
        return ""
    return url


def js_get_followers() -> str:
    """
    ブラウザで実行するJSコード。
    XプロフィールページからフォロワーとDM可否を取得する。
    使い方: mcp__claude-in-chrome__javascript_tool で実行
    戻り値: { followers: "1.2万", dmEnabled: true/false }
    """
    return """
(function() {
    // verified_followers リンクのテキストからフォロワー数を取得
    const el = document.querySelector('a[href*="verified_followers"]');
    let followers = '';
    if (el) {
        const m = el.innerText.match(/([\\d.,万千億]+)\\s*フォロワー/);
        followers = m ? m[1] : '';
    }
    // フォロー中リンクも試す（ログイン不要の場合）
    if (!followers) {
        const links = [...document.querySelectorAll('a[href*="/followers"]')];
        for (const link of links) {
            const m = link.innerText.match(/([\\d.,万千億]+)\\s*フォロワー/);
            if (m) { followers = m[1]; break; }
        }
    }
    // DM ボタンの有無
    const dmBtn = document.querySelector('[data-testid="sendDMFromProfile"]');
    return {
        followers: followers,
        dmEnabled: !!dmBtn
    };
})()
"""
