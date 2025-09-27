import os
from github import Github
from agents.triage import triage_issue
from agents.fix import fix_bug


# Made the function async to handle async agent calls.
async def orchestrate_issue(payload: dict):
    g = Github(os.getenv("GITHUB_TOKEN"))

    issue_data = payload.get("issue", {})
    repo_full = payload.get("repository", {}).get("full_name")
    issue_num = issue_data.get("number")

    if not repo_full or not issue_num:
        print("Orchestrator: Missing repo/issue info.")
        return

    issue_text = f"{issue_data.get('title', '')}\n\n{issue_data.get('body', '')}"
    label = triage_issue(issue_text)

    try:
        repo = g.get_repo(repo_full)
        gh_issue = repo.get_issue(number=issue_num)

        if label:
            gh_issue.add_to_labels(label)
            print(f"Orchestrator: Added label '{label}' to issue #{issue_num}.")

        if label == "bug":
            print(f"Orchestrator: Label is 'bug', handing off to fix_bug agent.")
           # await the async fix_bug function.
            await fix_bug(issue_num, repo_full, gh_issue)

    except Exception as e:
        print(f"Orchestrator: An error occurred: {e}")
