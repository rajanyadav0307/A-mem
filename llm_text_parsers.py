"""
Plain-text prompt templates, section-marker parsers, and validation logic
for the robust A-MEM system. Replaces JSON-schema LLM calls with plain-text
prompts that work with any LLM backend (Ollama, SGLang, OpenAI, etc.).
"""

import json
import re
import logging
from typing import Dict, List, Any, Optional, Callable

logger = logging.getLogger("amem_robust")

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` fences from LLM output."""
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*\n?', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n?\s*```$', '', text, flags=re.MULTILINE)
    return text.strip()


def parse_with_json_fallback(response: str, plain_text_parser: Callable, *parser_args) -> Any:
    """Try JSON parsing first; fall back to section-marker parsing.

    Many models emit valid JSON even without strict mode, so we try that first
    for best-of-both-worlds compatibility.
    """
    try:
        cleaned = strip_markdown_fences(response)
        result = json.loads(cleaned)
        if isinstance(result, dict):
            return result
    except (json.JSONDecodeError, ValueError):
        pass
    return plain_text_parser(response, *parser_args)


# ---------------------------------------------------------------------------
# List parsing helpers
# ---------------------------------------------------------------------------

def _parse_list_items(text: str) -> List[str]:
    """Parse a section of text into a list of items.

    Handles:
      - Bullet points (-, *, numbered)
      - Comma-separated values
      - One item per line
    """
    if not text or not text.strip():
        return []

    lines = text.strip().splitlines()
    items: List[str] = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Strip bullet markers
        line = re.sub(r'^[\-\*\u2022]\s*', '', line)
        line = re.sub(r'^\d+[\.\)]\s*', '', line)
        # Strip surrounding quotes
        line = line.strip().strip('"').strip("'").strip()
        if not line:
            continue
        # If the line contains commas, split on them
        if ',' in line:
            for part in line.split(','):
                part = part.strip().strip('"').strip("'").strip()
                if part:
                    items.append(part)
        else:
            items.append(line)

    return items


def _extract_section(text: str, marker: str, next_markers: Optional[List[str]] = None) -> str:
    """Extract the text between *marker*: and the next known marker (or end).

    Args:
        text: Full LLM response
        marker: Section header to find (e.g. "KEYWORDS")
        next_markers: List of possible next section headers

    Returns:
        The text content of that section (may be empty string).
    """
    # Build a regex that finds the marker (case-insensitive) followed by a colon
    pattern = re.compile(
        rf'^\s*{re.escape(marker)}\s*:\s*(.*)$',
        re.IGNORECASE | re.MULTILINE,
    )
    match = pattern.search(text)
    if not match:
        return ""

    start = match.end()
    # The first line of content may be on the same line as the marker
    first_line = match.group(1).strip()

    # Find where the next section starts
    end = len(text)
    if next_markers:
        for nm in next_markers:
            nm_pattern = re.compile(
                rf'^\s*{re.escape(nm)}\s*:', re.IGNORECASE | re.MULTILINE
            )
            nm_match = nm_pattern.search(text, start)
            if nm_match and nm_match.start() < end:
                end = nm_match.start()

    rest = text[start:end].strip()
    if first_line and rest:
        return first_line + "\n" + rest
    return first_line or rest


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

ANALYZE_CONTENT_PROMPT = """Analyze the following content and provide:
1. KEYWORDS: The most important keywords (nouns, verbs, key concepts). Order from most to least important. At least three keywords. Do not include speaker names or time references.
2. CONTEXT: One sentence summarizing the main topic, key points, and purpose.
3. TAGS: Broad categories/themes for classification (domain, format, type). At least three tags.

Respond using EXACTLY this format (one section per header):

KEYWORDS: keyword1, keyword2, keyword3, ...
CONTEXT: A single sentence summarizing the content.
TAGS: tag1, tag2, tag3, ...

Content for analysis:
{content}"""


EVOLUTION_DECISION_PROMPT = """You are an AI memory evolution agent. Analyze the new memory note and its nearest neighbors to decide if evolution is needed.

New memory:
- Context: {context}
- Content: {content}
- Keywords: {keywords}

Nearest neighbor memories:
{nearest_neighbors_memories}

Based on the relationships between the new memory and its neighbors, decide:
- NO_EVOLUTION: The memory stands alone, no changes needed.
- STRENGTHEN: The new memory should be linked to some neighbors and its tags updated.
- UPDATE_NEIGHBOR: The neighbors' context/tags should be updated based on new understanding.
- STRENGTHEN_AND_UPDATE: Both strengthen and update neighbors.

Respond using EXACTLY this format:
DECISION: <one of NO_EVOLUTION, STRENGTHEN, UPDATE_NEIGHBOR, STRENGTHEN_AND_UPDATE>
REASON: <brief explanation>"""


STRENGTHEN_DETAILS_PROMPT = """Given the new memory and its neighbors, provide updated connections and tags.

New memory:
- Content: {content}
- Keywords: {keywords}

Neighbor memories:
{nearest_neighbors_memories}

Which neighbor indices should the new memory connect to? What tags best describe this memory?

Respond using EXACTLY this format:
CONNECTIONS: 0, 2, 3
TAGS: tag1, tag2, tag3, ..."""


UPDATE_NEIGHBORS_PROMPT = """Given the new memory and its neighbor memories, update each neighbor's context and tags based on a holistic understanding of all these memories together.

New memory:
- Content: {content}
- Context: {context}

Neighbor memories:
{nearest_neighbors_memories}

For each neighbor (indexed 0 to {max_neighbor_idx}), provide updated context and tags. If no change is needed, repeat the original values.

Respond using EXACTLY this format (one block per neighbor):

NEIGHBOR 0:
CONTEXT: updated context sentence
TAGS: tag1, tag2, tag3

NEIGHBOR 1:
CONTEXT: updated context sentence
TAGS: tag1, tag2, tag3

(continue for all {neighbor_count} neighbors)"""


FOCUSED_KEYWORDS_PROMPT = """List exactly 5 keywords that capture the main concepts of the following text. Output only the keywords, comma-separated, nothing else.

Text: {content}"""


# ---------------------------------------------------------------------------
# Parsers for each call site
# ---------------------------------------------------------------------------

def parse_analyze_content(response: str, content: str = "") -> Dict[str, Any]:
    """Parse the analyze_content LLM response.

    Returns:
        {"keywords": [...], "context": "...", "tags": [...]}
    """
    def _section_parse(resp: str, content_text: str = "") -> Dict[str, Any]:
        keywords_text = _extract_section(resp, "KEYWORDS", ["CONTEXT", "TAGS"])
        context_text = _extract_section(resp, "CONTEXT", ["TAGS", "KEYWORDS"])
        tags_text = _extract_section(resp, "TAGS", ["KEYWORDS", "CONTEXT"])

        keywords = _parse_list_items(keywords_text)
        context = context_text.strip() if context_text.strip() else ""
        tags = _parse_list_items(tags_text)

        return {"keywords": keywords, "context": context, "tags": tags}

    result = parse_with_json_fallback(response, _section_parse, content)

    # Validate / repair
    result = validate_analysis_result(result, content)
    return result


def parse_evolution_decision(response: str) -> Dict[str, str]:
    """Parse the evolution decision response.

    Returns:
        {"decision": "NO_EVOLUTION|STRENGTHEN|UPDATE_NEIGHBOR|STRENGTHEN_AND_UPDATE",
         "reason": "..."}
    """
    def _section_parse(resp: str) -> Dict[str, str]:
        decision_text = _extract_section(resp, "DECISION", ["REASON"])
        reason_text = _extract_section(resp, "REASON", ["DECISION"])

        decision = decision_text.strip().upper().replace(" ", "_")
        # Normalize common variants
        valid_decisions = {
            "NO_EVOLUTION", "STRENGTHEN", "UPDATE_NEIGHBOR",
            "STRENGTHEN_AND_UPDATE"
        }
        if decision not in valid_decisions:
            # Try to infer from keywords
            resp_upper = resp.upper()
            if "STRENGTHEN" in resp_upper and "UPDATE" in resp_upper:
                decision = "STRENGTHEN_AND_UPDATE"
            elif "STRENGTHEN" in resp_upper:
                decision = "STRENGTHEN"
            elif "UPDATE" in resp_upper:
                decision = "UPDATE_NEIGHBOR"
            else:
                decision = "NO_EVOLUTION"

        return {"decision": decision, "reason": reason_text.strip()}

    result = parse_with_json_fallback(response, _section_parse)

    # Map JSON keys if we got JSON
    if "should_evolve" in result:
        should_evolve = result.get("should_evolve", False)
        actions = result.get("actions", [])
        if not should_evolve:
            decision = "NO_EVOLUTION"
        elif "strengthen" in actions and "update_neighbor" in actions:
            decision = "STRENGTHEN_AND_UPDATE"
        elif "strengthen" in actions:
            decision = "STRENGTHEN"
        elif "update_neighbor" in actions:
            decision = "UPDATE_NEIGHBOR"
        else:
            decision = "NO_EVOLUTION"
        result = {"decision": decision, "reason": ""}

    if "decision" not in result:
        result = {"decision": "NO_EVOLUTION", "reason": ""}

    return result


def parse_strengthen_details(response: str) -> Dict[str, Any]:
    """Parse the strengthen details response.

    Returns:
        {"connections": [int, ...], "tags": [str, ...]}
    """
    def _section_parse(resp: str) -> Dict[str, Any]:
        conn_text = _extract_section(resp, "CONNECTIONS", ["TAGS"])
        tags_text = _extract_section(resp, "TAGS", ["CONNECTIONS"])

        # Parse connections as integers
        connections = []
        for item in _parse_list_items(conn_text):
            try:
                connections.append(int(item.strip()))
            except (ValueError, TypeError):
                pass

        tags = _parse_list_items(tags_text)
        return {"connections": connections, "tags": tags}

    result = parse_with_json_fallback(response, _section_parse)

    # Map from JSON keys if needed
    if "suggested_connections" in result and "connections" not in result:
        result["connections"] = [int(x) for x in result.get("suggested_connections", []) if isinstance(x, (int, float))]
    if "tags_to_update" in result and "tags" not in result:
        result["tags"] = result.get("tags_to_update", [])

    result.setdefault("connections", [])
    result.setdefault("tags", [])
    return result


def parse_update_neighbors(response: str, num_neighbors: int) -> List[Dict[str, Any]]:
    """Parse the update neighbors response.

    Returns:
        [{"context": "...", "tags": [...]}, ...] — one per neighbor
    """
    def _section_parse(resp: str, n_neighbors: int) -> List[Dict[str, Any]]:
        neighbors = []
        for i in range(n_neighbors):
            # Try to find NEIGHBOR i: block
            # Look for "NEIGHBOR i:" or "NEIGHBOR i\n"
            pattern = re.compile(
                rf'NEIGHBOR\s+{i}\s*:', re.IGNORECASE
            )
            match = pattern.search(resp)
            if not match:
                neighbors.append({"context": "", "tags": []})
                continue

            # Find the end of this neighbor block (next NEIGHBOR or end)
            next_pattern = re.compile(
                rf'NEIGHBOR\s+{i + 1}\s*:', re.IGNORECASE
            )
            next_match = next_pattern.search(resp, match.end())
            block_end = next_match.start() if next_match else len(resp)
            block = resp[match.end():block_end]

            ctx = _extract_section(block, "CONTEXT", ["TAGS"])
            tags_text = _extract_section(block, "TAGS", ["CONTEXT"])
            tags = _parse_list_items(tags_text)

            neighbors.append({"context": ctx.strip(), "tags": tags})

        return neighbors

    # Try JSON first
    try:
        cleaned = strip_markdown_fences(response)
        data = json.loads(cleaned)
        if isinstance(data, dict):
            contexts = data.get("new_context_neighborhood", [])
            tags_list = data.get("new_tags_neighborhood", [])
            neighbors = []
            for i in range(num_neighbors):
                ctx = contexts[i] if i < len(contexts) else ""
                tags = tags_list[i] if i < len(tags_list) else []
                neighbors.append({"context": ctx, "tags": tags})
            return neighbors
    except (json.JSONDecodeError, ValueError):
        pass

    return _section_parse(response, num_neighbors)


def parse_plain_text_answer(response: str) -> str:
    """Parse a plain-text answer response (for QA evaluation).

    If the model returned JSON with an "answer" field, extract it.
    Otherwise return the raw text.
    """
    try:
        cleaned = strip_markdown_fences(response)
        data = json.loads(cleaned)
        if isinstance(data, dict) and "answer" in data:
            return str(data["answer"])
    except (json.JSONDecodeError, ValueError):
        pass
    return response.strip()


def parse_relevant_parts(response: str) -> str:
    """Parse retrieve_memory_llm response.

    If JSON with "relevant_parts", extract it. Otherwise return raw text.
    """
    try:
        cleaned = strip_markdown_fences(response)
        data = json.loads(cleaned)
        if isinstance(data, dict) and "relevant_parts" in data:
            return str(data["relevant_parts"])
    except (json.JSONDecodeError, ValueError):
        pass
    return response.strip()


def parse_keywords_response(response: str) -> str:
    """Parse generate_query_llm response.

    If JSON with "keywords", extract it. Otherwise return raw text.
    """
    try:
        cleaned = strip_markdown_fences(response)
        data = json.loads(cleaned)
        if isinstance(data, dict) and "keywords" in data:
            return str(data["keywords"])
    except (json.JSONDecodeError, ValueError):
        pass
    return response.strip()


# ---------------------------------------------------------------------------
# Validation / heuristic repair
# ---------------------------------------------------------------------------

def validate_analysis_result(result: Dict[str, Any], content: str = "") -> Dict[str, Any]:
    """Validate and repair the analysis result.

    - If keywords is empty, extract capitalized words / nouns heuristically.
    - If context is empty, use the first sentence of content.
    - If tags is empty, derive from keywords.
    """
    if not isinstance(result, dict):
        result = {"keywords": [], "context": "", "tags": []}

    keywords = result.get("keywords", [])
    context = result.get("context", "")
    tags = result.get("tags", [])

    # Ensure lists
    if isinstance(keywords, str):
        keywords = _parse_list_items(keywords)
    if isinstance(tags, str):
        tags = _parse_list_items(tags)
    if isinstance(context, list):
        context = " ".join(context)

    # Repair empty keywords from content
    if not keywords and content:
        keywords = _heuristic_keywords(content)

    # Repair empty context from content
    if not context and content:
        context = _heuristic_context(content)

    # Repair empty tags from keywords
    if not tags and keywords:
        tags = keywords[:3]

    result["keywords"] = keywords
    result["context"] = context
    result["tags"] = tags
    return result


def _heuristic_keywords(content: str, max_keywords: int = 5) -> List[str]:
    """Extract heuristic keywords from content text."""
    # Remove common stop words and extract significant words
    stop_words = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'shall', 'can', 'need', 'dare', 'ought',
        'used', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
        'as', 'into', 'through', 'during', 'before', 'after', 'above',
        'below', 'between', 'out', 'off', 'over', 'under', 'again',
        'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why',
        'how', 'all', 'both', 'each', 'few', 'more', 'most', 'other',
        'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
        'than', 'too', 'very', 'just', 'because', 'but', 'and', 'or',
        'if', 'while', 'about', 'up', 'it', 'its', 'i', 'me', 'my',
        'you', 'your', 'he', 'she', 'they', 'we', 'this', 'that', 'these',
        'those', 'what', 'which', 'who', 'whom', 'says', 'said', 'speaker',
    }
    words = re.findall(r'\b[a-zA-Z]{3,}\b', content)
    # Prefer capitalized words (likely proper nouns / key terms)
    scored = []
    seen = set()
    for w in words:
        w_lower = w.lower()
        if w_lower in stop_words or w_lower in seen:
            continue
        seen.add(w_lower)
        score = 2 if w[0].isupper() else 1
        scored.append((w_lower, score))

    scored.sort(key=lambda x: -x[1])
    return [w for w, _ in scored[:max_keywords]]


def _heuristic_context(content: str) -> str:
    """Extract a heuristic context sentence from content."""
    # Take the first sentence (up to period, question mark, or exclamation)
    match = re.match(r'(.+?[.!?])\s', content)
    if match:
        return match.group(1).strip()
    # Fallback: first 200 chars
    return content[:200].strip()


# ---------------------------------------------------------------------------
# Consolidation (T-MEM Module 2)
# ---------------------------------------------------------------------------

CONSOLIDATION_VERIFY_PROMPT = """You are checking whether several memory notes from a conversation can be merged into one note.

Notes (each with the date it was said):
{notes}

Choose exactly one label:
- SAME_FACT: the notes state the same fact, plan, or event (repeated or rephrased). Merging loses nothing.
- SMALL_TALK: the notes are greetings, thanks, praise, or encouragement with no distinct facts.
- DIFFERENT: the notes describe different facts, events, objects, or details, even if they sound similar.

If you are unsure, choose DIFFERENT.

Respond in this exact format:
LABEL: SAME_FACT, SMALL_TALK, or DIFFERENT
REASON: one sentence"""


CONSOLIDATION_MERGE_PROMPT = """Combine these memory notes from a conversation into ONE short note.

Notes:
{notes}

{label_rules}

Rules for every note you write:
- Name the speaker. Write each date as an absolute date like "17 July 2023".
- Never write relative times such as "next month", "last week", "yesterday" or "two days ago". Convert them using the date of the note they came from. Example: "next month" said on 17 July 2023 becomes "in August 2023"; "last week" said on 6 July 2023 becomes "in the week before 6 July 2023".
- Keep every name, place, number, and distinct fact. Do not add anything that is not in the notes.
- Do not copy the notes one after another. Write one short summary that is shorter than the notes together.

Example
Notes:
1. Sam, 3 March 2022: Next month I'm starting pottery classes at the Oak Street studio - can't wait!
2. Sam, 20 April 2022: Wow, pottery at Oak Street starts next week. So excited!
CONTENT: Sam planned to start pottery classes at the Oak Street studio. On 3 March 2022 Sam said they would start in April 2022; on 20 April 2022 Sam said they would start in the week after 20 April 2022.
CONTEXT: Sam's pottery classes at the Oak Street studio.
{feedback}
Respond in this exact format:
CONTENT: the combined note
CONTEXT: one sentence describing the topic"""


CONSOLIDATION_LABEL_RULES = {
    "SAME_FACT": (
        "These notes repeat the same fact, plan, or event. State it once, then list when it was "
        "mentioned. If the notes disagree on a detail (such as a time), keep each version with its date."
    ),
    "SMALL_TALK": (
        "These notes are small talk (greetings, thanks, praise, encouragement). Write one sentence "
        "saying who said what kind of thing to whom, and list the dates. Keep any names, places, or "
        "specific things mentioned."
    ),
}


CONSOLIDATION_MERGE_FEEDBACK = """
Your previous attempt had these problems. Fix all of them:
{problems}
"""


CONSOLIDATION_LABELS = ("SAME_FACT", "SMALL_TALK", "DIFFERENT")


_CONSOLIDATION_SPEAKER = re.compile(r"^Speaker\s+(.+?)says\s*:\s*")
_CONSOLIDATION_DATE = re.compile(r"(\d{1,2})\s+([A-Za-z]+),?\s+(\d{4})")


def format_consolidation_notes(notes: List[Any]) -> str:
    """Numbered note list for the consolidation prompts.

    Renders "Speaker Xsays : text" with timestamp "2:31 pm on 17 July, 2023"
    as "1. X, 17 July 2023: text" so the LLM does not copy the raw format.
    """
    lines = []
    for i, note in enumerate(notes, start=1):
        content = note.content or ""
        match = _CONSOLIDATION_SPEAKER.match(content)
        speaker = match.group(1).strip() if match else None
        body = content[match.end():] if match else content
        date_match = _CONSOLIDATION_DATE.search(note.timestamp or "")
        date = " ".join(date_match.groups()) if date_match else (note.timestamp or "unknown date")
        who = f"{speaker}, {date}" if speaker else date
        lines.append(f"{i}. {who}: {body.strip()}")
    return "\n".join(lines)


def parse_consolidation_verdict(response: str) -> Dict[str, str]:
    """Parse the verify response.

    Returns:
        {"label": "SAME_FACT|SMALL_TALK|DIFFERENT", "reason": "..."}

    Anything unreadable becomes DIFFERENT, so a bad response never merges notes.
    """
    def _section_parse(resp: str) -> Dict[str, str]:
        label_text = _extract_section(resp, "LABEL", ["REASON"])
        reason_text = _extract_section(resp, "REASON", ["LABEL"])
        return {"label": label_text, "reason": reason_text}

    result = parse_with_json_fallback(response or "", _section_parse)
    label = str(result.get("label", "")).strip().upper().replace(" ", "_").strip(".")
    if label not in CONSOLIDATION_LABELS:
        found = [cand for cand in CONSOLIDATION_LABELS if cand in label]
        label = found[0] if len(found) == 1 else "DIFFERENT"
    return {"label": label, "reason": str(result.get("reason", "")).strip()}


def parse_consolidation_merge(response: str) -> Dict[str, str]:
    """Parse the merge response.

    Returns:
        {"content": "...", "context": "..."}  (content is "" if missing)
    """
    def _section_parse(resp: str) -> Dict[str, str]:
        content = _extract_section(resp, "CONTENT", ["CONTEXT"])
        context = _extract_section(resp, "CONTEXT", ["CONTENT"])
        return {"content": content, "context": context}

    result = parse_with_json_fallback(response or "", _section_parse)
    content = " ".join(str(result.get("content", "")).split())
    context = " ".join(str(result.get("context", "")).split())
    return {"content": content, "context": context}


# ---------------------------------------------------------------------------
# Conflict handling (T-MEM Module 3)
# ---------------------------------------------------------------------------

STATE_EXTRACT_PROMPT = """A person said this in a conversation on {date}:
{speaker}: {text}

Does it state something about the speaker's own situation that can change over time?
Examples: a job or business, where they live, a relationship, health, a plan or project and how far it has got, something they own, a regular habit, a goal.
Greetings, thanks, praise, questions and opinions about other people do not count.

Respond in this exact format:
STATE: YES or NO
TOPIC: if YES, 2 to 5 words naming the thing, starting with the speaker's name (e.g. "Jon's dance studio"); if NO, write NONE
STATUS: if YES, a short phrase for its status at that time (e.g. "searching for a location"); if NO, write NONE"""


CONFLICT_CHECK_PROMPT = """Two things the same person said about the same topic, in date order:

OLDER ({old_date}): {old_text}
NEWER ({new_date}): {new_text}

How does the NEWER statement relate to the OLDER one? Choose exactly one label:
- SAME: it repeats the same fact or status.
- PROGRESS: the same plan or situation has moved forward (for example, searching -> found -> running).
- CHANGE: the old fact is no longer true and has been replaced (for example, a new job, moved house, quit).
- CONTRADICTION: the two cannot both be true and it is not a natural change over time.
- COMPATIBLE: both are true at the same time; the newer one adds something without replacing the older one.
- UNRELATED: they are not about the same thing.

If you are unsure, choose COMPATIBLE.

Respond in this exact format:
LABEL: one of SAME, PROGRESS, CHANGE, CONTRADICTION, COMPATIBLE, UNRELATED
REASON: one sentence"""


CONFLICT_LABELS = ("SAME", "PROGRESS", "CHANGE", "CONTRADICTION", "COMPATIBLE", "UNRELATED")


def parse_state_extract(response: str) -> Dict[str, Any]:
    """Parse the state-extraction response.

    Returns:
        {"is_state": bool, "topic": str, "status": str}. Unreadable -> not a state.
    """
    text = response or ""
    is_state = _extract_section(text, "STATE", ["TOPIC", "STATUS"]).strip().upper().startswith("YES")
    topic = " ".join(_extract_section(text, "TOPIC", ["STATUS", "STATE"]).split()).strip('"')
    status = " ".join(_extract_section(text, "STATUS", ["TOPIC", "STATE"]).split()).strip('"')
    if not is_state or not topic or topic.upper() == "NONE":
        return {"is_state": False, "topic": "", "status": ""}
    return {"is_state": True, "topic": topic, "status": "" if status.upper() == "NONE" else status}


def parse_conflict_label(response: str) -> Dict[str, str]:
    """Parse the conflict-check response. Unreadable -> COMPATIBLE (changes nothing)."""
    text = response or ""
    label = _extract_section(text, "LABEL", ["REASON"]).strip().upper().replace(" ", "_").strip(".")
    if label not in CONFLICT_LABELS:
        found = [cand for cand in CONFLICT_LABELS if cand in label]
        label = found[0] if len(found) == 1 else "COMPATIBLE"
    return {"label": label, "reason": " ".join(_extract_section(text, "REASON", ["LABEL"]).split())}


STATE_EXTRACT_PROMPT_STRICT = """A person said this in a conversation on {date}:
{speaker}: {text}

Does it state a concrete, checkable fact about the speaker's own life that could change later?
Count ONLY:
- a job, business or studio and its status (e.g. looking for a location, opened, expanding, closed)
- where they live or a move
- a relationship status
- a step in a specific plan (e.g. researched agencies, applied, passed interviews)
- signing up for, starting, or stopping a specific activity, class or routine
- something specific they bought, own, lost or got
Do NOT count: feelings, thanks, praise, encouragement, wishes, general enthusiasm ("going for my dreams"), opinions, questions, or facts about other people.

Respond in this exact format:
STATE: YES or NO
TOPIC: if YES, the specific thing, as "<speaker>'s <thing>" in 2 to 5 words (e.g. "Jon's dance studio", "Caroline's adoption", "Melanie's pottery class"); if NO, write NONE
STATUS: if YES, its concrete status at that time in a few words (e.g. "searching for a location", "applied to agency"); if NO, write NONE"""


CONFLICT_VERIFY_PROMPT = """Two things the same person said, in date order:

OLDER ({old_date}): {old_text}
NEWER ({new_date}): {new_text}

After the NEWER statement, is the OLDER statement no longer true, because it was replaced or contradicted?
Answer YES only if the NEWER statement clearly says something that cannot be true at the same time as the OLDER one.
Thanks, encouragement, feelings, plans, or simply moving forward do not count. If unsure, answer NO.

Respond in this exact format:
ANSWER: YES or NO
QUOTE: the exact words from the NEWER statement that show it, or NONE"""


def parse_conflict_verify(response: str, newer_text: str) -> Dict[str, Any]:
    """Parse the verification answer. Confirmed only with YES and a quote found in the newer text."""
    text = response or ""
    yes = _extract_section(text, "ANSWER", ["QUOTE"]).strip().upper().startswith("YES")
    quote = " ".join(_extract_section(text, "QUOTE", ["ANSWER"]).split()).strip().strip('"').strip("'")
    norm = lambda s: re.sub(r"[^a-z0-9 ]", "", " ".join(s.lower().split()))  # noqa: E731
    quoted = bool(quote) and quote.upper() != "NONE" and norm(quote) in norm(newer_text)
    return {"confirmed": yes and quoted, "answer_yes": yes, "quote": quote}
