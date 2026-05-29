TOOL_UI_MESSAGES: dict[str, str] = {
    # Velora's own tools
    "get_db_info":          "🔌 Connecting to your database…",
    "retrieve_schema":      "🔍 Searching for relevant tables…",
    "execute_query":        "⚡ Querying your data…",
    "add_sample_query":     "🧠 Learning from this question…",

    # Deep Agents built-in tools
    "write_todos":          "📋 Breaking down your question…",
    "write_file":           "💾 Saving intermediate results…",
    "read_file":            "📂 Reading saved results…",
    "edit_file":            "✏️  Updating saved results…",
    "ls":                   "📁 Checking workspace…",
    "glob":                 "🔎 Scanning files…",
    "grep":                 "🔎 Searching through data…",
    "compact_conversation": "🗜️  Optimising memory…",
    "task":                 "🤖 Delegating to sub-agent…",
}


def friendly_tool_message(tool_name: str) -> str:
    return TOOL_UI_MESSAGES.get(tool_name, f"⚙️  Running {tool_name}…")