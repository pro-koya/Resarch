"""
Article Summarizer
P0: 抽出型要約（頻度ベース）
P1: LLM要約（環境変数 SUMMARIZER=llm で切替）
"""

import os
import re
from collections import Counter

import requests
from bs4 import BeautifulSoup


def html_to_text(html: str) -> str:
    """HTML を平文に変換。"""
    if not html:
        return ""
    soup = BeautifulSoup(html, "lxml")
    # スクリプト・スタイル除去
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    # 連続空白を正規化
    return re.sub(r"\s+", " ", text).strip()


def split_sentences(text: str) -> list[str]:
    """テキストを文単位に分割。日本語・英語混在対応。"""
    # 日本語の句点、英語のピリオド+空白で分割
    sentences = re.split(r"(?<=[。．.!?！？])\s*", text)
    return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]


def extractive_summarize(text: str, num_sentences: int = 3) -> str:
    """頻度ベースの抽出型要約。重要な文を上位N件選択。"""
    sentences = split_sentences(text)
    if not sentences:
        return text[:300] if text else ""

    if len(sentences) <= num_sentences:
        return " ".join(sentences)

    # 単語頻度スコア計算
    words = re.findall(r"\w{2,}", text.lower())
    word_freq = Counter(words)

    # ストップワード的な高頻度語を除外（上位5%）
    if word_freq:
        threshold = max(word_freq.values()) * 0.95
        word_freq = Counter({w: f for w, f in word_freq.items() if f < threshold})

    # 各文のスコア計算
    scored = []
    for i, sent in enumerate(sentences):
        sent_words = re.findall(r"\w{2,}", sent.lower())
        if not sent_words:
            score = 0.0
        else:
            score = sum(word_freq.get(w, 0) for w in sent_words) / len(sent_words)
        # 先頭の文にボーナス（記事冒頭は重要な傾向）
        if i == 0:
            score *= 1.5
        scored.append((i, score, sent))

    # スコア上位を選択し、元の出現順に並べる
    scored.sort(key=lambda x: x[1], reverse=True)
    top = sorted(scored[:num_sentences], key=lambda x: x[0])

    return " ".join(t[2] for t in top)


def _is_mostly_english(text: str) -> bool:
    """テキストが主に英語かどうかを簡易判定。"""
    ascii_chars = sum(1 for c in text[:500] if c.isascii() and c.isalpha())
    total_alpha = sum(1 for c in text[:500] if c.isalpha())
    if total_alpha == 0:
        return False
    return ascii_chars / total_alpha > 0.7


def llm_summarize(text: str, num_sentences: int = 3) -> str:
    """LLM APIを使った要約。未設定の場合は extractive にフォールバック。"""
    api_key = os.environ.get("LLM_API_KEY", "")
    api_url = os.environ.get("LLM_API_URL", "")
    model = os.environ.get("LLM_MODEL", "")

    if not all([api_key, api_url, model]):
        print("[WARN] LLM API 未設定。extractive 要約にフォールバックします。")
        return extractive_summarize(text, num_sentences)

    prompt = (
        f"以下の記事を{num_sentences}文以内で**必ず日本語で**要約してください。"
        f"英語の記事であっても日本語に翻訳して要約してください。"
        f"事実のみを簡潔に述べ、洞察や意見は含めないでください。"
        f"要約のみを出力し、前置きや説明は不要です。\n\n"
        f"{text[:3000]}"
    )

    try:
        resp = requests.post(
            api_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500,
            },
            timeout=60,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        else:
            print(f"[WARN] LLM API error {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"[WARN] LLM API 呼び出し失敗: {e}。extractive にフォールバック。")

    return extractive_summarize(text, num_sentences)


def summarize(html_content: str, method: str = "extractive", num_sentences: int = 3) -> str:
    """記事の HTML コンテンツを要約する。"""
    text = html_to_text(html_content)
    if not text:
        return "(本文なし)"

    if method == "llm":
        return llm_summarize(text, num_sentences)
    return extractive_summarize(text, num_sentences)
