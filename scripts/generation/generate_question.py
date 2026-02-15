"""
Factle Daily Question Generator

Generates a new Factle question each day by:
1. Searching for current events, celebrations, cultural moments
2. Picking a creative, topical topic and generating a ranked-list question
3. Verifying the answer order against authoritative web sources (with retries)
4. Re-verifying any corrections
5. Appending to questions.json and logging the run

Usage:
    python generate_question.py [--dry-run]

Environment variables required:
    GITHUB_TOKEN   - GitHub PAT for GitHub Models API
    TAVILY_API_KEY - Tavily API key for web search
"""

import json
import os
import sys
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

from openai import OpenAI
from tavily import TavilyClient

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
QUESTIONS_FILE = REPO_ROOT / "factle" / "questions.json"
BACKUP_FILE = REPO_ROOT / "factle" / "backup_questions.json"
LOG_FILE = REPO_ROOT / "factle" / "generation_log.json"

MAX_TOPIC_ATTEMPTS = 5
MAX_VERIFY_RETRIES = 3  # inner retries per question before moving to next topic
CET = timezone(timedelta(hours=1))

# GitHub Models endpoint
GITHUB_MODELS_ENDPOINT = "https://models.inference.ai.azure.com"
LLM_MODEL = "gpt-5"

# Topics to filter out — sensitive, violent, or inappropriate
BLOCKED_TOPICS = [
    "shooting", "murder", "killing", "terrorism", "terrorist",
    "epstein", "abuse", "assault", "scandal", "death toll",
    "massacre", "genocide", "suicide", "rape", "trafficking",
    "war crime", "hate crime", "extremism", "conspiracy",
]

# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------


def create_clients():
    """Initialize LLM and search clients."""
    github_token = os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN")
    tavily_key = os.environ.get("TAVILY_API_KEY")

    if not github_token:
        raise EnvironmentError("GITHUB_TOKEN or GH_PAT environment variable required")
    if not tavily_key:
        raise EnvironmentError("TAVILY_API_KEY environment variable required")

    llm = OpenAI(
        base_url=GITHUB_MODELS_ENDPOINT,
        api_key=github_token,
    )
    search = TavilyClient(api_key=tavily_key)
    return llm, search


# ---------------------------------------------------------------------------
# Step 0: Load history
# ---------------------------------------------------------------------------


def load_questions():
    """Load existing questions from questions.json."""
    if QUESTIONS_FILE.exists():
        with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("questions", [])
    return []


def load_log():
    """Load generation log."""
    if LOG_FILE.exists():
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"runs": []}


def get_previous_questions_summary(questions):
    """Build a concise summary of previous questions for similarity checking."""
    return "\n".join(
        f"- ID {q['id']}: {q['question']}" for q in questions
    )


# ---------------------------------------------------------------------------
# Step 1: Discover current topics
# ---------------------------------------------------------------------------


def is_topic_appropriate(topic_text):
    """Filter out inappropriate or sensitive topics."""
    lower = topic_text.lower()
    return not any(blocked in lower for blocked in BLOCKED_TOPICS)


def discover_topics(llm, search, run_log):
    """Search for current events, celebrations, and cultural moments, then
    rank them for Factle suitability with creative question ideas."""
    today = datetime.now(CET)
    today_str = today.strftime("%B %d, %Y")

    # Multiple diverse search queries to capture different angles
    search_queries = [
        f"major sports events tournaments happening {today_str}",
        f"cultural events celebrations holidays {today.strftime('%B %Y')}",
        f"award ceremonies festivals conferences {today.strftime('%B %Y')}",
        f"notable events news highlights past week {today_str}",
        f"famous birthdays national days {today.strftime('%B %d')}",
    ]

    all_search_results = []
    raw_search_log = []

    for query in search_queries:
        try:
            results = search.search(query=query, max_results=5)
            items = results.get("results", [])
            all_search_results.extend(items)
            raw_search_log.append({
                "query": query,
                "results": [
                    {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("content", "")[:200]}
                    for r in items
                ],
            })
        except Exception as e:
            raw_search_log.append({"query": query, "error": str(e)})

    run_log["step1_topic_discovery"] = {"searches": raw_search_log}

    # Build context from all search results
    search_context = "\n".join(
        f"- {r.get('title', '')}: {r.get('content', '')[:200]}"
        for r in all_search_results
    )

    # Ask LLM to extract and rank creative, topical questions
    response = llm.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a creative game show host designing daily trivia for 'Factle'. "
                    "Factle questions are 'rank the top 5 in order' questions where ORDER "
                    "matters and answers are objectively verifiable.\n\n"
                    "IMPORTANT RULES:\n"
                    "- Questions MUST be inspired by current events, recent happenings, "
                    "celebrations, sports events, cultural moments, or seasonal themes.\n"
                    "- Questions must NOT be generic (like 'top 5 most populous countries' "
                    "or 'top 5 largest economies') — those are boring and overused.\n"
                    "- Questions must NOT be about sensitive topics like violence, crime, "
                    "abuse, shootings, political scandals, or anything offensive.\n"
                    "- Be creative! Connect current events to interesting ranked lists.\n\n"
                    "GREAT EXAMPLES of creative, topical questions:\n"
                    "- During Winter Olympics: 'Top 5 countries by Winter Olympics all-time "
                    "gold medals'\n"
                    "- After Super Bowl: 'Top 5 NFL teams by number of Super Bowl wins'\n"
                    "- During Grammy season: 'Top 5 artists with most Grammy Awards ever'\n"
                    "- Valentine's Day: 'Top 5 countries that spend the most on Valentine\\'s Day'\n"
                    "- During FIFA World Cup: 'Top 5 World Cup all-time top scorers'\n"
                    "- Near a country's national day: 'Top 5 exports of that country'\n"
                    "- Famous person's birthday: 'Top 5 highest-grossing films starring that actor'\n"
                    "- During award season: 'Top 5 films with most Oscar wins'\n"
                    "- During a music festival: 'Top 5 best-selling albums of all time'\n"
                    "- During a space event: 'Top 5 longest manned space missions'\n\n"
                    "BAD EXAMPLES (too generic, avoid these):\n"
                    "- 'Top 5 most populated countries'\n"
                    "- 'Top 5 largest countries by area'\n"
                    "- 'Top 5 biggest economies'\n"
                    "- 'Top 5 tallest mountains'\n"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Today is {today_str}. Here are current events and happenings:\n\n"
                    f"{search_context}\n\n"
                    "Based on these events, suggest 8-10 creative Factle questions that "
                    "are DIRECTLY inspired by what's happening right now. Each question "
                    "must have objectively verifiable, ordered answers.\n\n"
                    "For each suggestion, explain the connection to current events.\n\n"
                    "At the end, include 2-3 seasonal/cultural fallbacks (related to this "
                    "time of year, but not generic knowledge questions).\n\n"
                    "Return ONLY a JSON object with a 'topics' key containing an array of "
                    "objects with keys:\n"
                    "- 'topic': the current event or theme inspiring this question\n"
                    "- 'suggested_question': the exact Factle question to ask\n"
                    "- 'connection': why this is relevant right now"
                ),
            },
        ],
        response_format={"type": "json_object"},
    )

    try:
        result = json.loads(response.choices[0].message.content)
        topics = []
        if isinstance(result, list):
            topics = result
        elif "topics" in result:
            topics = result["topics"]
        else:
            for v in result.values():
                if isinstance(v, list):
                    topics = v
                    break

        # Filter out inappropriate topics
        filtered = [
            t for t in topics
            if is_topic_appropriate(t.get("topic", "") + " " + t.get("suggested_question", ""))
        ]

        run_log["step1_topic_discovery"]["ranked_topics"] = filtered
        run_log["step1_topic_discovery"]["filtered_count"] = len(topics) - len(filtered)
        return filtered
    except (json.JSONDecodeError, IndexError, KeyError) as e:
        run_log["step1_topic_discovery"]["error"] = str(e)

    return []


# ---------------------------------------------------------------------------
# Step 2a: Similarity check
# ---------------------------------------------------------------------------


def is_too_similar(llm, topic, suggested_question, previous_summary, attempt_log):
    """Check if a proposed topic is too similar to previous questions."""
    if not previous_summary.strip():
        attempt_log["similarity_check"] = {"skipped": True, "reason": "No previous questions"}
        return False

    response = llm.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You compare trivia questions to detect duplicates or near-duplicates.",
            },
            {
                "role": "user",
                "content": (
                    f"Proposed new topic: {topic}\n"
                    f"Suggested question: {suggested_question}\n\n"
                    f"Here are all previously used questions:\n{previous_summary}\n\n"
                    "Is this new question too similar to any previous one? "
                    "Two questions are 'too similar' if they ask essentially the "
                    "same thing (e.g., 'largest countries by area' and 'biggest "
                    "countries by land area'). Questions in the same broad category "
                    "but about different specifics are fine (e.g., 'tallest mountains' "
                    "and 'longest rivers' are both geography but different enough).\n\n"
                    "Respond with ONLY a JSON object: {\"too_similar\": true/false, "
                    "\"reason\": \"brief explanation\"}"
                ),
            },
        ],
        response_format={"type": "json_object"},
    )

    try:
        result = json.loads(response.choices[0].message.content)
        attempt_log["similarity_check"] = result
        return result.get("too_similar", False)
    except (json.JSONDecodeError, KeyError):
        attempt_log["similarity_check"] = {"error": "Failed to parse response"}
        return False


# ---------------------------------------------------------------------------
# Step 2b: Generate question
# ---------------------------------------------------------------------------


def generate_question(llm, topic, suggested_question):
    """Generate a full Factle question with answers and distractors."""
    response = llm.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You create trivia questions for Factle, a game where players "
                    "must rank 5 items in the correct order. You must provide:\n"
                    "- A clear question\n"
                    "- Exactly 5 correct answers in the RIGHT ORDER (1st to 5th)\n"
                    "- Exactly 15 plausible but incorrect distractor options\n"
                    "- A suggested source URL where the answer can be verified\n\n"
                    "The distractors should be from the same category and realistic "
                    "enough that someone might confuse them with the correct answers. "
                    "All 20 options (5 correct + 15 distractors) must be unique."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Topic: {topic}\n"
                    f"Suggested question direction: {suggested_question}\n\n"
                    "Generate the Factle question. Return ONLY a JSON object with:\n"
                    "- \"question\": the question text\n"
                    "- \"answers\": array of exactly 5 correct answers in order "
                    "(index 0 = 1st place, index 4 = 5th place)\n"
                    "- \"distractors\": array of exactly 15 plausible wrong options\n"
                    "- \"source\": a URL where this ranking can be verified\n"
                    "- \"search_query\": a search query that would find an "
                    "authoritative source for verification"
                ),
            },
        ],
        response_format={"type": "json_object"},
    )

    try:
        return json.loads(response.choices[0].message.content)
    except (json.JSONDecodeError, IndexError):
        return None


# ---------------------------------------------------------------------------
# Step 2c: Verify via search
# ---------------------------------------------------------------------------


def search_for_verification(search, question_data, attempt_log, iteration=0):
    """Search the web for authoritative sources to verify the answer."""
    query = question_data.get("search_query", question_data.get("question", ""))
    results = search.search(query=query, max_results=5)

    sources = []
    for r in results.get("results", []):
        sources.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": r.get("content", "")[:500],
        })

    log_key = f"verification_search_iter{iteration}"
    attempt_log[log_key] = {
        "query": query,
        "sources_found": [{"title": s["title"], "url": s["url"]} for s in sources],
    }

    return sources


# ---------------------------------------------------------------------------
# Step 2d: Cross-check with retry support
# ---------------------------------------------------------------------------


def cross_check(llm, question_text, answers, sources, attempt_log, iteration=0):
    """Cross-check answers against web sources. Works for both initial and
    corrected answers."""
    sources_text = "\n\n".join(
        f"Source: {s['title']} ({s['url']})\n{s['content']}" for s in sources
    )

    response = llm.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a meticulous fact-checker. You compare a trivia answer "
                    "against authoritative web source data. The ORDER of the answers "
                    "is critical — this is a ranking question.\n\n"
                    "Be very careful about ordering. If the source clearly shows a "
                    "different order, you MUST correct it. If you can verify some "
                    "answers but not the exact order, try to provide the correct "
                    "order from the source data.\n\n"
                    "If the source data contains enough information to determine the "
                    "correct answers and order, use it — don't give up too easily."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Question: {question_text}\n\n"
                    f"Proposed answers (in order, 1st to 5th):\n"
                    f"1. {answers[0]}\n"
                    f"2. {answers[1]}\n"
                    f"3. {answers[2]}\n"
                    f"4. {answers[3]}\n"
                    f"5. {answers[4]}\n\n"
                    f"Web source data:\n{sources_text}\n\n"
                    "Based on the source data, are these answers correct AND in the "
                    "right order?\n\n"
                    "Respond with ONLY a JSON object:\n"
                    "- \"status\": one of \"VERIFIED\", \"CORRECTED\", or \"UNVERIFIABLE\"\n"
                    "- \"corrected_answers\": (only if CORRECTED) array of 5 answers in "
                    "the correct order\n"
                    "- \"corrected_source\": (only if CORRECTED) the URL of the most "
                    "authoritative source used for correction\n"
                    "- \"reason\": detailed explanation of your finding, including what "
                    "the sources say\n\n"
                    "Use VERIFIED if the answers match the sources in both "
                    "content and order.\n"
                    "Use CORRECTED if you can determine the right answers/order from "
                    "the sources. Provide the corrected list.\n"
                    "Use UNVERIFIABLE ONLY if the source data truly has no relevant "
                    "information about this question."
                ),
            },
        ],
        response_format={"type": "json_object"},
    )

    try:
        result = json.loads(response.choices[0].message.content)
        log_key = f"cross_check_iter{iteration}"
        attempt_log[log_key] = {
            "status": result.get("status"),
            "reason": result.get("reason"),
            "proposed_answers": list(answers),
            "corrected_answers": result.get("corrected_answers"),
        }
        return result
    except (json.JSONDecodeError, IndexError):
        return {"status": "UNVERIFIABLE", "reason": "Failed to parse cross-check response"}


# ---------------------------------------------------------------------------
# Step 2e: Re-verify correction
# ---------------------------------------------------------------------------


def re_verify_correction(llm, search, question_text, corrected_answers, attempt_log, iteration=0):
    """
    When answers were corrected by the cross-check, do a second round of
    verification with a more targeted search to confirm the corrected order.
    """
    top_two = corrected_answers[:2]
    specific_query = (
        f"{question_text} "
        f"{top_two[0]} vs {top_two[1]} ranking list"
    )

    results = search.search(query=specific_query, max_results=5)
    sources_text = "\n\n".join(
        f"Source: {r.get('title', '')} ({r.get('url', '')})\n{r.get('content', '')[:500]}"
        for r in results.get("results", [])
    )

    response = llm.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a fact-checker performing a SECOND verification of a "
                    "corrected trivia answer. A previous check corrected the order "
                    "of answers. You must confirm or reject this corrected order "
                    "using the new source data provided. Be very strict about ordering."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Question: {question_text}\n\n"
                    f"Corrected answers (in order, 1st to 5th):\n"
                    f"1. {corrected_answers[0]}\n"
                    f"2. {corrected_answers[1]}\n"
                    f"3. {corrected_answers[2]}\n"
                    f"4. {corrected_answers[3]}\n"
                    f"5. {corrected_answers[4]}\n\n"
                    f"Additional source data:\n{sources_text}\n\n"
                    "Based on this additional source data, is the corrected order "
                    "confirmed?\n\n"
                    "Respond with ONLY a JSON object:\n"
                    "- \"status\": \"CONFIRMED\" or \"REJECTED\"\n"
                    "- \"reason\": brief explanation\n"
                    "- \"best_source\": URL of the most authoritative source"
                ),
            },
        ],
        response_format={"type": "json_object"},
    )

    try:
        result = json.loads(response.choices[0].message.content)
        log_key = f"re_verify_iter{iteration}"
        attempt_log[log_key] = {
            "search_query": specific_query,
            "sources_found": [
                {"title": r.get("title", ""), "url": r.get("url", "")}
                for r in results.get("results", [])
            ],
            "status": result.get("status"),
            "reason": result.get("reason"),
            "best_source": result.get("best_source"),
        }
        return result
    except (json.JSONDecodeError, IndexError):
        attempt_log[f"re_verify_iter{iteration}"] = {"error": "Failed to parse response"}
        return {"status": "REJECTED", "reason": "Failed to parse re-verification response"}


# ---------------------------------------------------------------------------
# Step 3: Validate and assemble
# ---------------------------------------------------------------------------


def validate_question_entry(entry):
    """Validate the final question entry before saving."""
    errors = []

    if not entry.get("question"):
        errors.append("Missing question text")

    answers = entry.get("answers", [])
    if len(answers) != 5:
        errors.append(f"Expected 5 answers, got {len(answers)}")

    options = entry.get("options", [])
    if len(options) != 20:
        errors.append(f"Expected 20 options, got {len(options)}")

    # Check all answers are in options
    for a in answers:
        if a not in options:
            errors.append(f"Answer '{a}' not found in options")

    # Check for duplicates in options
    if len(set(options)) != len(options):
        errors.append("Duplicate options found")

    if not entry.get("source"):
        errors.append("Missing source URL")

    return errors


def assemble_question_entry(date_str, question_data, answers, source_url, next_id):
    """Assemble the final question JSON entry."""
    # Combine answers + distractors into the 20 options
    distractors = question_data.get("distractors", [])
    options = list(answers) + distractors

    return {
        "id": next_id,
        "date": date_str,
        "question": question_data["question"],
        "options": options,
        "answers": list(answers),
        "source": source_url,
    }


# ---------------------------------------------------------------------------
# Step 4: Write results
# ---------------------------------------------------------------------------


def save_question(entry, questions):
    """Append the new question to questions.json."""
    questions.append(entry)
    data = {"questions": questions}
    with open(QUESTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def save_log(log):
    """Save the generation log."""
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=4, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Backup fallback
# ---------------------------------------------------------------------------


def use_backup_question(date_str, next_id, questions):
    """Pick a backup question that hasn't been used yet."""
    if not BACKUP_FILE.exists():
        return None

    with open(BACKUP_FILE, "r", encoding="utf-8") as f:
        backup_data = json.load(f)

    used_questions = {q["question"] for q in questions}
    backups = backup_data.get("questions", [])

    for backup in backups:
        if backup["question"] not in used_questions:
            entry = {
                "id": next_id,
                "date": date_str,
                "question": backup["question"],
                "options": backup["options"],
                "answers": backup["answers"],
                "source": backup["source"],
            }
            return entry

    return None


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


def run(dry_run=False):
    """Main generation pipeline."""
    print("=" * 60)
    print("Factle Daily Question Generator")
    print("=" * 60)

    # Initialize
    llm, search = create_clients()
    questions = load_questions()
    log = load_log()
    today = datetime.now(CET)
    date_str = today.strftime("%Y-%m-%d")
    next_id = max((q.get("id", 0) for q in questions), default=0) + 1
    previous_summary = get_previous_questions_summary(questions)

    # Check if question already exists for today
    if any(q.get("date") == date_str for q in questions):
        print(f"Question for {date_str} already exists. Skipping.")
        return

    run_log = {
        "date": date_str,
        "topics_discovered": [],
        "attempts": [],
        "result": "pending",
    }

    print(f"\nDate: {date_str}")
    print(f"Previous questions: {len(questions)}")
    print(f"Next ID: {next_id}")

    # ------------------------------------------------------------------
    # Step 1: Discover topics
    # ------------------------------------------------------------------
    print("\n--- Step 1: Discovering current topics ---")
    topics = discover_topics(llm, search, run_log)

    if not topics:
        print("ERROR: No topics discovered. Using backup.")
        entry = use_backup_question(date_str, next_id, questions)
        if entry:
            run_log["result"] = "backup_no_topics"
            if not dry_run:
                save_question(entry, questions)
            print(f"Backup question saved: {entry['question']}")
        else:
            run_log["result"] = "failed_no_backup"
            print("CRITICAL: No backup questions available either!")
        log["runs"].append(run_log)
        if not dry_run:
            save_log(log)
        return

    run_log["topics_discovered"] = [
        {
            "topic": t.get("topic", "unknown"),
            "suggested_question": t.get("suggested_question", "unknown"),
            "connection": t.get("connection", ""),
        }
        for t in topics
    ]
    print(f"Found {len(topics)} candidate topics:")
    for i, t in enumerate(topics):
        print(f"  {i+1}. [{t.get('topic', 'N/A')}] {t.get('suggested_question', 'N/A')}")
        print(f"      Connection: {t.get('connection', 'N/A')}")

    # ------------------------------------------------------------------
    # Step 2: Attempt loop (outer: topics, inner: verify retries)
    # ------------------------------------------------------------------
    success = False
    final_entry = None

    for attempt_idx, topic_info in enumerate(topics[:MAX_TOPIC_ATTEMPTS]):
        topic = topic_info.get("topic", "")
        suggested_q = topic_info.get("suggested_question", "")
        attempt_log = {
            "topic": topic,
            "suggested_question": suggested_q,
            "connection": topic_info.get("connection", ""),
            "status": "pending",
            "reason": "",
            "verify_iterations": 0,
        }

        print(f"\n{'='*50}")
        print(f"Attempt {attempt_idx + 1}/{MAX_TOPIC_ATTEMPTS}: {topic}")
        print(f"Question: {suggested_q}")
        print(f"{'='*50}")

        # 2a. Similarity check
        print("  [Step 2a] Checking similarity...")
        if is_too_similar(llm, topic, suggested_q, previous_summary, attempt_log):
            print("  ❌ Too similar to a previous question. Skipping.")
            attempt_log["status"] = "skipped_similar"
            attempt_log["reason"] = "Too similar to previous question"
            run_log["attempts"].append(attempt_log)
            continue

        # 2b. Generate question
        print("  [Step 2b] Generating question...")
        question_data = generate_question(llm, topic, suggested_q)
        if not question_data or "answers" not in question_data or len(question_data.get("answers", [])) != 5:
            print("  ❌ Failed to generate valid question. Skipping.")
            attempt_log["status"] = "generation_failed"
            attempt_log["reason"] = "LLM did not return valid question structure"
            run_log["attempts"].append(attempt_log)
            continue

        question_text = question_data["question"]
        attempt_log["generated_question"] = {
            "question": question_text,
            "answers": question_data["answers"],
            "distractors": question_data.get("distractors", []),
            "suggested_source": question_data.get("source", ""),
        }

        print(f"  Question: {question_text}")
        print(f"  Initial answers: {question_data['answers']}")

        # ----------------------------------------------------------
        # Inner verification loop: retry up to MAX_VERIFY_RETRIES
        # for the SAME question, correcting the order each time
        # ----------------------------------------------------------
        current_answers = list(question_data["answers"])
        source_url = question_data.get("source", "")
        verified = False

        for verify_iter in range(MAX_VERIFY_RETRIES):
            attempt_log["verify_iterations"] = verify_iter + 1
            print(f"\n  --- Verification iteration {verify_iter + 1}/{MAX_VERIFY_RETRIES} ---")
            print(f"  Current answers: {current_answers}")

            # 2c. Search for verification sources
            print(f"  [Step 2c] Searching for verification sources...")
            sources = search_for_verification(search, question_data, attempt_log, iteration=verify_iter)
            if not sources:
                print("  ❌ No sources found for verification.")
                attempt_log[f"verify_iter{verify_iter}_result"] = "no_sources"
                continue

            print(f"  Found {len(sources)} sources")
            for s in sources:
                print(f"    - {s['title'][:60]} ({s['url'][:60]})")

            # 2d. Cross-check
            print(f"  [Step 2d] Cross-checking answers against sources...")
            check_result = cross_check(
                llm, question_text, current_answers, sources,
                attempt_log, iteration=verify_iter
            )
            status = check_result.get("status", "UNVERIFIABLE")
            print(f"  Cross-check result: {status}")
            print(f"  Reason: {check_result.get('reason', 'N/A')}")

            if status == "VERIFIED":
                print("  ✅ Answers verified!")
                verified = True
                break

            elif status == "CORRECTED":
                corrected = check_result.get("corrected_answers", [])
                if len(corrected) != 5:
                    print(f"  ❌ Correction has {len(corrected)} answers (need 5). Retrying...")
                    continue

                print(f"  Corrected answers: {corrected}")

                # 2e. Re-verify the correction with a targeted search
                print(f"  [Step 2e] Re-verifying corrected order...")
                re_verify = re_verify_correction(
                    llm, search, question_text, corrected,
                    attempt_log, iteration=verify_iter
                )
                re_status = re_verify.get("status", "REJECTED")
                print(f"  Re-verification result: {re_status}")
                print(f"  Reason: {re_verify.get('reason', 'N/A')}")

                if re_status == "CONFIRMED":
                    print("  ✅ Corrected order confirmed!")
                    current_answers = corrected
                    source_url = re_verify.get("best_source", source_url)
                    if check_result.get("corrected_source"):
                        source_url = check_result["corrected_source"]
                    verified = True
                    break
                else:
                    # Use the corrected answers as the new baseline
                    # and try verifying again in the next iteration
                    print("  ⚠️ Correction not confirmed. Using corrected answers")
                    print("     as new baseline for next verification attempt...")
                    current_answers = corrected
                    continue

            else:
                # UNVERIFIABLE — try with different search terms next iteration
                print("  ⚠️ Unverifiable. Will retry with current answers...")
                # Modify search query for next attempt
                question_data["search_query"] = (
                    f"{question_text} {current_answers[0]} {current_answers[1]} ranking"
                )
                continue

        if not verified:
            print(f"  ❌ Failed to verify after {MAX_VERIFY_RETRIES} iterations. Moving to next topic.")
            attempt_log["status"] = "verification_exhausted"
            attempt_log["reason"] = f"Could not verify after {MAX_VERIFY_RETRIES} iterations"
            run_log["attempts"].append(attempt_log)
            continue

        # If we reach here, we have verified answers
        print("\n  [Step 3] Assembling final question entry...")
        final_entry = assemble_question_entry(
            date_str, question_data, current_answers, source_url, next_id
        )
        validation_errors = validate_question_entry(final_entry)

        if validation_errors:
            print(f"  ❌ Validation failed: {validation_errors}")
            attempt_log["status"] = "validation_failed"
            attempt_log["reason"] = "; ".join(validation_errors)
            run_log["attempts"].append(attempt_log)
            continue

        # Success!
        print("  ✅ Question validated successfully!")
        attempt_log["status"] = "success"
        attempt_log["question_id"] = next_id
        attempt_log["final_answers"] = current_answers
        attempt_log["final_source"] = source_url
        run_log["attempts"].append(attempt_log)
        success = True
        break

    # ------------------------------------------------------------------
    # Fallback to backup
    # ------------------------------------------------------------------
    if not success:
        print("\n--- All attempts failed. Using backup question. ---")
        final_entry = use_backup_question(date_str, next_id, questions)
        if final_entry:
            run_log["result"] = "backup"
            print(f"Backup question: {final_entry['question']}")
        else:
            run_log["result"] = "failed"
            print("CRITICAL: No backup questions available!")
            log["runs"].append(run_log)
            if not dry_run:
                save_log(log)
            sys.exit(1)
    else:
        run_log["result"] = "success"
        run_log["question_id"] = next_id

    # ------------------------------------------------------------------
    # Step 4: Save
    # ------------------------------------------------------------------
    if dry_run:
        print("\n--- DRY RUN — not saving ---")
        print(json.dumps(final_entry, indent=2, ensure_ascii=False))
    else:
        print("\n--- Saving question ---")
        save_question(final_entry, questions)
        print(f"Saved to {QUESTIONS_FILE}")

    log["runs"].append(run_log)
    if not dry_run:
        save_log(log)
        print(f"Log saved to {LOG_FILE}")

    print("\n✅ Done!")
    print(f"Question: {final_entry['question']}")
    print(f"Answers: {final_entry['answers']}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate daily Factle question")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without saving to files",
    )
    args = parser.parse_args()
    run(dry_run=args.dry_run)
