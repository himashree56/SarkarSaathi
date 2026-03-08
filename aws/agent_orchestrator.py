"""
SarkarSaathi — Bedrock Agent Orchestrator Configuration
This script outlines the configuration for the Amazon Bedrock Agent.
"""

AGENT_CONFIG = {
    "agent_name": "SarkarSaathi-Orchestrator",
    "instruction": (
        "You are SarkarSaathi, an expert AI assistant for Indian government schemes. "
        "Your goal is to help users find and apply for schemes by extracting their profile, "
        "matching schemes, and providing detailed guidance. "
        "\n\nORCHESTRATION STRATEGY:"
        "\n1. First, use 'extractProfile' to turn the user's message into structured data. Use the 'current_profile' from session memory if available."
        "\n2. Once you have a profile, use 'getSchemes' to retrieve the best matches."
        "\n3. Use 'manageSession' to persist the state (profile, history, summary) for the user's next visit."
        "\n4. Respond to the user in their preferred language (Hindi/English) in a helpful, concise manner."
    ),
    "model_id": "anthropic.claude-3-5-sonnet-20240620-v1:0", # High reasoning for orchestration
    "action_groups": [
        {
            "name": "SarkarSaathiTools",
            "description": "Access to scheme database, profile extraction, and session management.",
            "api_spec_file": "agent_api_spec.json",
            "lambda_arn": "arn:aws:lambda:REGION:ACCOUNT_ID:function:sarkarsaathi-backend"
        }
    ]
}

def print_setup_guide():
    print("SarkarSaathi Bedrock Agent Setup Guide")
    print("======================================")
    print(f"1. Create Agent: {AGENT_CONFIG['agent_name']}")
    print(f"2. Set Model: {AGENT_CONFIG['model_id']}")
    print("3. Set Instructions (copy-paste from summary)")
    print("4. Add Action Group:")
    for ag in AGENT_CONFIG['action_groups']:
        print(f"   - Name: {ag['name']}")
        print(f"   - API Spec: {ag['api_spec_file']}")
        print(f"   - Lambda: {ag['lambda_arn']}")
    print("5. Save and Prepare Agent.")
    print("6. Integrate with Frontend via Bedrock Agent Runtime API.")

if __name__ == "__main__":
    print_setup_guide()
