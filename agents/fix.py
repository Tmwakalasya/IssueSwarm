import os
import re
import asyncio
from github import Github
import google.generativeai as genai
model = genai.GenerativeModel('gemini-2.5-pro')

async def fix_bug(issue_number, repo_full_name, gh_issue):
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    g = Github(os.getenv("GITHUB_TOKEN"))
    repo = g.get_repo(repo_full_name)
    issue_body = gh_issue.body or ''

    # File parsing from diagram: Regex for paths in body
    file_paths = re.findall(r'[\w/]+\.(py|js|ts|md)', issue_body)[:3]
    file_contents = {}
    for path in file_paths:
        try:
            content = repo.get_contents(path).decoded_content.decode()[:4000]
            file_contents[path] = content
        except:
            pass

    prompt = f"Analyze bug: {gh_issue.title} {issue_body}. Files: {file_contents}. Suggest fix code."
    try:
        response = await asyncio.to_thread(model.generate_content, prompt)  # Async wrapper
        fix_suggestion = response.text
        comment = f"🤖 AI Fix Suggestion for #{issue_number}:\n```python\n{fix_suggestion}\n```"
        gh_issue.create_comment(comment)
        print("[fix_bug] Comment posted.")
    except Exception as e:
        print("[fix_bug] AI/Comment error:", e)
        gh_issue.create_comment("🤖 Fix attempt failed—human needed.")