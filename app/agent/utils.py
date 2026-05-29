def extract_agent_answer(result: dict) -> str:
    last = result["messages"][-1]
    content = last.content if hasattr(last, "content") else str(last)
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(str(block.get("text", "")))
            else:
                parts.append(str(block))
        content = "".join(parts)
    return str(content).strip()
