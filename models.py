from dataclasses import dataclass, field


@dataclass
class PersonRecord:
    name: str
    company: str = ""
    x_url: str = ""
    facebook_url: str = ""
    youtube_url: str = ""
    instagram_url: str = ""
    company_hp: str = ""
    email: str = ""
    contact_form_url: str = ""
    blog_url: str = ""
    youtube_email: str = ""
    notes: str = ""

    def to_row(self) -> list:
        return [
            self.name,
            self.company,
            self.x_url,
            self.facebook_url,
            self.youtube_url,
            self.instagram_url,
            self.company_hp,
            self.email,
            self.contact_form_url,
            self.blog_url,
            self.youtube_email,
            self.notes,
        ]

    @classmethod
    def headers(cls) -> list:
        return [
            "名前", "会社・組織", "X(Twitter)", "Facebook", "YouTube",
            "Instagram", "会社HP", "メールアドレス", "問い合わせフォーム",
            "YouTubeメール", "備考",
        ]
