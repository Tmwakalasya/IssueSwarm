async def orchestrate_issue(payload: dict):
    issue = payload.get("issue", {})
    repo = payload.get("repository", {}).get("full_name", "unknown/repo")
    action = payload.get("action")

    print("=== Webhook Triggered ===")
    print(f"Repo: {repo}")
    print(f"Issue #{issue.get('number')} - {issue.get('title')}")
    print(f"Action: {action}")
    print("==========================")

    # You can return something here to help debugging
    return {"repo": repo, "issue": issue.get("number"), "action": action}
