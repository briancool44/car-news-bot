import os
import json
import requests
from datetime import datetime
import subprocess

# 【設定】
NEWS_API_KEY = os.environ.get('NEWS_API_KEY')
CLAUDE_API_KEY = os.environ.get('CLAUDE_API_KEY')
NEWS_API_URL = "https://newsapi.org/v2/everything"

def get_news():
    """News APIからニュースを取得"""
    params = {
        'q': '中古車',  # 検索キーワード
        'language': 'ja',  # 日本語
        'sortBy': 'publishedAt',  # 新しい順
        'pageSize': 50,  # 50個取得
        'apiKey': NEWS_API_KEY
    }
    
    response = requests.get(NEWS_API_URL, params=params)
    articles = response.json().get('articles', [])
    return articles

def evaluate_articles_with_claude(articles):
    """Claudeに記事を評価してもらう"""
    
    # 記事をテキスト化
    articles_text = "\n\n".join([
        f"【記事{i+1}】\n"
        f"タイトル: {article['title']}\n"
        f"説明: {article['description']}\n"
        f"リンク: {article['url']}"
        for i, article in enumerate(articles[:20])  # 最初の20個だけ使う
    ])
    
    # Claudeに指示
    prompt = f"""以下の中古車関連ニュース記事から、
最も重要で質の高い記事を5個選んでください。

【記事リスト】
{articles_text}

【指示】
- 中古車業界に大きな影響を与えそうな記事を優先
- 具体的なビジネスニュース（新サービス、システム導入など）を優先
- つまらない小ネタは避ける

【返す形式】
記事1: [タイトル]
記事2: [タイトル]
...
のように、選んだ記事のタイトルだけを返してください。
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
            "model": "claude-opus-4-6",
            "max_tokens": 500,
            "messages": [{"role": "user", "content": prompt}]
        }
    )
    
    result = response.json()
    return result['content'][0]['text']

def create_html(articles, claude_result):
    """HTMLファイルを作成"""
    
    timestamp = datetime.now().strftime("%Y年%m月%d日 %H:%M")
    
    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>中古車ニュース - {timestamp}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #007bff;
            padding-bottom: 10px;
        }}
        .claude-summary {{
            background-color: #e7f3ff;
            border-left: 4px solid #007bff;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .articles {{
            background-color: white;
            padding: 20px;
            border-radius: 4px;
            margin-top: 20px;
        }}
        .article {{
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 1px solid #ddd;
        }}
        .article:last-child {{
            border-bottom: none;
        }}
        .article-title {{
            font-size: 1.2em;
            font-weight: bold;
            color: #007bff;
            margin-bottom: 8px;
        }}
        .article-desc {{
            color: #555;
            line-height: 1.6;
            margin-bottom: 10px;
        }}
        .article-link {{
            color: #007bff;
            text-decoration: none;
        }}
        .article-link:hover {{
            text-decoration: underline;
        }}
        .timestamp {{
            color: #999;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <h1>📰 中古車ニュース - 毎日まとめ</h1>
    <p class="timestamp">更新日時: {timestamp}</p>
    
    <div class="claude-summary">
        <h2>🤖 Claudeが選んだ今日のトップニュース</h2>
        <pre style="white-space: pre-wrap; word-wrap: break-word;">{claude_result}</pre>
    </div>
    
    <div class="articles">
        <h2>📋 今日のニュース一覧（全{len(articles)}件）</h2>
"""
    
    for i, article in enumerate(articles[:30], 1):  # 最初の30個表示
        html += f"""
        <div class="article">
            <div class="article-title">{i}. {article['title']}</div>
            <div class="article-desc">{article.get('description', 'N/A')}</div>
            <a href="{article['url']}" class="article-link" target="_blank">記事を読む →</a>
        </div>
"""
    
    html += """
    </div>
</body>
</html>
"""
    
    return html

def save_and_commit(html_content):
    """HTMLをファイルに保存してGithubにコミット"""
    
    # ファイル名を日付で作成
    filename = f"news_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    filepath = f"news/{filename}"
    
    # フォルダ作成
    os.makedirs('news', exist_ok=True)
    
    # ファイル保存
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ ファイル保存: {filepath}")
    
    # Githubにコミット
    os.system(f'git config user.email "bot@example.com"')
    os.system(f'git config user.name "news-bot"')
    os.system('git add news/')
    os.system(f'git commit -m "📰 Daily news update: {datetime.now().strftime("%Y-%m-%d %H:%M")}"')
    os.system('git push origin main')
    
    print("✅ Githubにアップロード完了！")

def main():
    """メイン処理"""
    print("🤖 中古車ニュースボット起動...")
    
    # ニュース取得
    print("📡 News APIからニュースを取得中...")
    articles = get_news()
    print(f"✅ {len(articles)}個のニュースを取得しました")
    
    # Claude評価
    print("🧠 Claudeが記事を評価中...")
    claude_result = evaluate_articles_with_claude(articles)
    print("✅ 評価完了")
    
    # HTML作成
    print("🎨 HTMLを作成中...")
    html = create_html(articles, claude_result)
    
    # 保存してコミット
    print("💾 ファイル保存とアップロード中...")
    save_and_commit(html)
    
    print("🎉 完了！")

if __name__ == "__main__":
    main()
