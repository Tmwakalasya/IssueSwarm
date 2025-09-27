import os
import google.generativeai as genai

model = genai.GenerativeModel('gemini-2.5-pro')

def triage_issue(issue_text):
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    prompt = (
        f"Classify this GitHub issue strictly as one of: 'bug', 'feature', or 'question'. "
        f"Output ONLY the label, nothing else. Issue: {issue_text}"
    )
    try:
        response = model.generate_content(prompt)
        label = response.text.strip().lower()
        if label not in ['bug', 'feature', 'question']:
            label = 'question'
        return label
    except Exception as e:
        print(f"Triage error: {e}")
        return 'question'
