import sys, os
sys.path.insert(0, 'aws')
os.environ['REGION'] = 'us-east-1'
os.environ['DATA_BUCKET'] = 'sarkarsaathi-data'
os.environ['SESSIONS_TABLE'] = 'ss-sessions'
os.environ['CACHE_TABLE'] = 'ss-cache'
os.environ['BEDROCK_MODEL'] = 'anthropic.claude-3-haiku-20240307-v1:0'

from lambda_function import rule_based_extract, _extract_needs, NEEDS_KEYWORDS, bedrock_extract

q = 'I am a 50 year old male farmer from rural Maharashtra, annual income 80000 rupees'

print("=" * 60)
print("Query:", q)
print("=" * 60)

# Rule-based
rule = rule_based_extract(q)
print("\n[Rule-based]")
print("  needs:", rule.get('needs'))

# Check which keywords match
print("\n[Keyword scan]")
q_lower = q.lower()
for need, kws in NEEDS_KEYWORDS.items():
    for kw in kws:
        if kw.lower() in q_lower:
            print(f"  MATCH: {need} <- '{kw}'")

# Bedrock
print("\n[Bedrock] calling Claude...")
try:
    b = bedrock_extract(q)
    print("  needs:", b.get('needs'))
    print("  full:", b)
except Exception as e:
    print("  ERROR:", e)
