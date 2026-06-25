import os
import json
import requests
from datetime import datetime

NEWS_API_KEY = os.environ.get('NEWS_API_KEY')
CLAUDE_API_KEY = os.environ.get('CLAUDE_API_KEY')
NEWS_API_URL = "https://newsapi.org/v2/everything"

def get_news():
    """中古車業界に絞った検索キーワードで記事取得"""
    all_articles = []

    queries = [
        {'q': '中古車 OR 中古自動車 OR カーオークション', 'language': 'ja'},
        {'q': 'used car dealer OR used car auction OR car remarketing', 'language': 'en'},
        {'q': 'automotive used vehicle market OR second hand car industry', 'language': 'en'},
    ]

    for q in queries:
        params = {
            **q,
            'sortBy': 'publishedAt',
            'pageSize': 20,
            'apiKey': NEWS_API_KEY
        }
        response = requests.get(NEWS_API_URL, params=params)
        articles = response.json().get('articles', [])
        all_articles.extend(articles)

    # URLで重複除去・タイトルなし除去
    seen = set()
    unique = []
    for a in all_articles:
        if a['url'] not in seen and a.get('title') and a['title'] != '[Removed]':
            seen.add(a['url'])
            unique.append(a)

    return unique

def evaluate_articles_with_claude(articles):
    """Claudeが中古車業界視点で5記事を選び、日本語で要約する"""

    articles_text = "\n\n".join([
        f"【記事{i+1}】\n"
        f"タイトル: {article['title']}\n"
        f"内容: {article.get('description', 'なし')}\n"
        f"URL: {article['url']}"
        for i, article in enumerate(articles[:30])
    ])

    prompt = f"""あなたは中古車業界のアナリストです。
以下のニュース記事の中から、中古車業界（販売店、オークション、買取、EV中古車、相場動向など）に関係する記事を厳選して5つ選び、それぞれを日本語で要約してください。

中古車と全く関係のない記事（スポーツ、音楽、医療、政治など）は絶対に選ばないでください。

【記事リスト】
{articles_text}

【返す形式】必ず以下のJSON形式で返してください。他のテキストは不要です。
[
  {{
    "rank": 1,
    "title": "記事の元タイトル（そのまま）",
    "url": "記事のURL",
    "summary": "この記事の内容を中古車業界目線で3〜4文で日本語要約",
    "point": "業界への影響・注目ポイントを1文で"
  }},
  ...
]
"""

    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers,
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 2000,
            "messages": [{"role": "user", "content": prompt}]
        }
    )

    result = response.json()

    if response.status_code != 200 or 'error' in result:
        error_info = result.get('error', result)
        raise RuntimeError(f"Claude API error: {error_info}")

    text = result['content'][0]['text']

    # JSONを抽出してパース
    start = text.find('[')
    end = text.rfind(']') + 1
    if start == -1 or end == 0:
        raise RuntimeError(f"Claude returned unexpected format: {text}")

    return json.loads(text[start:end])

def create_html(picks):
    """厳選5記事のHTMLを作成"""

    timestamp = datetime.now().strftime("%Y年%m月%d日 %H:%M")

    cards_html = ""
    for item in picks:
        cards_html += f"""
        <div class="card">
            <div class="rank">#{item['rank']}</div>
            <h2 class="card-title">
                <a href="{item['url']}" target="_blank">{item['title']}</a>
            </h2>
            <p class="summary">{item['summary']}</p>
            <div class="point">💡 {item['point']}</div>
            <a href="{item['url']}" class="read-more" target="_blank">元記事を読む →</a>
        </div>
"""

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>中古車ニュース - {timestamp}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Segoe UI', sans-serif;
            background: #f0f2f5;
            padding: 20px;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
        }}
        header {{
            text-align: center;
            padding: 30px 0 20px;
        }}
        header h1 {{
            font-size: 1.8em;
            color: #1a1a2e;
        }}
        header p {{
            color: #888;
            margin-top: 6px;
            font-size: 0.9em;
        }}
        .subtitle {{
            background: #007bff;
            color: white;
            text-align: center;
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 24px;
            font-weight: bold;
        }}
        .card {{
            background: white;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            border-left: 5px solid #007bff;
        }}
        .rank {{
            font-size: 0.85em;
            font-weight: bold;
            color: #007bff;
            margin-bottom: 8px;
        }}
        .card-title {{
            font-size: 1.15em;
            margin-bottom: 12px;
            line-height: 1.5;
        }}
        .card-title a {{
            color: #1a1a2e;
            text-decoration: none;
        }}
        .card-title a:hover {{
            color: #007bff;
            text-decoration: underline;
        }}
        .summary {{
            color: #444;
            line-height: 1.8;
            font-size: 0.95em;
            margin-bottom: 14px;
        }}
        .point {{
            background: #fff8e1;
            border-left: 3px solid #ffc107;
            padding: 10px 14px;
            border-radius: 4px;
            color: #555;
            font-size: 0.9em;
            margin-bottom: 14px;
        }}
        .read-more {{
            color: #007bff;
            text-decoration: none;
            font-size: 0.9em;
            font-weight: bold;
        }}
        .read-more:hover {{ text-decoration: underline; }}
        footer {{
            text-align: center;
            color: #aaa;
            font-size: 0.8em;
            padding: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🚗 中古車業界ニュース</h1>
            <p>更新日時: {timestamp}</p>
        </header>
        <div class="subtitle">🤖 Claudeが厳選した今日のトップ5ニュース</div>
        {cards_html}
        <footer>Powered by Claude &amp; NewsAPI</footer>
    </div>
</body>
</html>
"""
    return html

def save_and_commit(html_content):
    """HTMLをファイルに保存してGithubにコミット"""

    filename = f"news_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    filepath = f"news/{filename}"

    os.makedirs('news', exist_ok=True)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"✅ ファイル保存: {filepath}")

    # index.html を更新
    news_files = sorted(
        [f for f in os.listdir('news') if f.startswith('news_') and f.endswith('.html')],
        reverse=True
    )
    index_html = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>中古車ニュース一覧</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f0f2f5; }
        h1 { color: #1a1a2e; border-bottom: 3px solid #007bff; padding-bottom: 10px; margin-bottom: 20px; }
        ul { list-style: none; padding: 0; }
        li { background: white; margin: 10px 0; padding: 16px 20px; border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.08); border-left: 4px solid #007bff; }
        a { color: #1a1a2e; text-decoration: none; font-size: 1.05em; font-weight: bold; }
        a:hover { color: #007bff; }
    </style>
</head>
<body>
    <h1>🚗 中古車業界ニュース一覧</h1>
    <ul>
"""
    for f in news_files:
        date_str = f.replace('news_', '').replace('.html', '')
        try:
            dt = datetime.strptime(date_str, '%Y%m%d_%H%M%S')
            label = dt.strftime('%Y年%m月%d日 %H:%M')
        except:
            label = date_str
        index_html += f'        <li><a href="{f}">{label} のニュース</a></li>\n'
    index_html += """    </ul>
</body>
</html>"""
    with open('news/index.html', 'w', encoding='utf-8') as f:
        f.write(index_html)
    print("✅ index.html 更新")

    os.system('git config user.email "bot@example.com"')
    os.system('git config user.name "news-bot"')
    os.system('git add news/')
    os.system(f'git commit -m "📰 Daily news update: {datetime.now().strftime("%Y-%m-%d %H:%M")}"')
    os.system('git push origin main')

    print("✅ Githubにアップロード完了！")

def main():
    print("🤖 中古車ニュースボット起動...")

    print("📡 News APIからニュースを取得中...")
    articles = get_news()
    print(f"✅ {len(articles)}個のニュースを取得しました")

    print("🧠 Claudeが記事を厳選・要約中...")
    picks = evaluate_articles_with_claude(articles)
    print(f"✅ {len(picks)}記事を厳選しました")

    print("🎨 HTMLを作成中...")
    html = create_html(picks)

    print("💾 ファイル保存とアップロード中...")
    save_and_commit(html)

    print("🎉 完了！")

if __name__ == "__main__":
    main()
