"""
Factle Daily Question Generator

Generates a new Factle question each day by:
1. Searching for current trending topics
2. Picking a suitable topic and generating a ranked-list question
3. Verifying the answer order against authoritative web sources
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
CET = timezone(timedelta(hours=1))

# GitHub Models endpoint
GITHUB_MODELS_ENDPOINT = "https://models.inference.ai.azure.com"
LLM_MODEL = "gpt-4o-mini"

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


def discover_topics(llm, search):
    """Search for current trending topics and rank them for Factle suitability."""
    today_str = datetime.now(CET).strftime("%B %d, %Y")

    # Search for trending news / events
    search_results = search.search(
        query=f"top trending news events today {today_str}",
        max_results=10,
    )

    # Build context from search results
    search_context = "\n".join(
        f"- {r.get('title', '')}: {r.get('content', '')[:200]}"
        for r in search_results.get("results", [])
    )

    # Ask LLM to extract and rank topics suitable for Factle
    response = llm.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a trivia question designer for a game called Factle. "
                    "Factle questions are always 'rank the top 5' style questions "
                    "where the ORDER matters. Good questions have objectively verifiable "
                    "ranked answers from authoritative sources (e.g., 'Top 5 countries "
                    "by GDP', 'Top 5 Olympic gold medal winners in swimming'). "
                    "Bad questions are subjective or have answers that change hourly."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Today is {today_str}. Here are current trending news topics:\n\n"
                    f"{search_context}\n\n"
                    "Based on these, suggest up to 8 topics that could be turned into "
                    "'rank the top 5 in order' trivia questions with objectively verifiable, "
                    "ordered answers. For each topic, briefly explain what the question "
                    "could be.\n\n"
                    "Also include 2-3 general knowledge topics (not from the news) as "
                    "fallback options at the end of the list.\n\n"
                    "Return ONLY a JSON array of objects with keys 'topic' and "
                    "'suggested_question'. No other text."
                ),
            },
        ],
        temperature=0.7,
        response_format={"type": "json_object"},
    )

    try:
        result = json.loads(response.choices[0].message.content)
        # Handle both {"topics": [...]} and direct [...] formats
        if isinstance(result, list):
            return result
        if "topics" in result:
            return result["topics"]
        # Try to find any list value in the response
        for v in result.values():
            if isinstance(v, list):
                return v
    except (json.JSONDecodeError, IndexError, KeyError):
        pass

    return []


# ---------------------------------------------------------------------------
# Step 2a: Similarity check
# ---------------------------------------------------------------------------


def is_too_similar(llm, topic, suggested_question, previous_summary):
    """Check if a proposed topic is too similar to previous questions."""
    if not previous_summary.strip():
        return False  # No previous questions, can't be similar

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
        temperature=0.0,
        response_format={"type": "json_object"},
    )

    try:
        result = json.loads(response.choices[0].message.content)
        return result.get("too_similar", False)
    except (json.JSONDecodeError, KeyError):
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
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    try:
        return json.loads(response.choices[0].message.content)
    except (json.JSONDecodeError, IndexError):
        return None


# ---------------------------------------------------------------------------
# Step 2c: Verify via search
# ---------------------------------------------------------------------------


def search_for_verification(search, question_data):
    """Search the web for authoritative sources to verify the answer."""
    query = question_data.get("search_query", question_data.get("question", ""))
    results = search.search(query=query, max_results=5)

    # Build verification context from search results
    sources = []
    for r in results.get("results", []):
        sources.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": r.get("content", "")[:500],
        })

    return sources


# ---------------------------------------------------------------------------
# Step 2d: Cross-check
# ---------------------------------------------------------------------------


def cross_check(llm, question_data, sources):
    """Cross-check generated answers against web sources."""
    sources_text = "\n\n".join(
        f"Source: {s['title']} ({s['url']})\n{s['content']}" for s in sources
    )

    response = llm.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a fact-checker. You compare a generated trivia answer "
                    "against authoritative web source data. The ORDER of the answers "
                    "is critical — this is a ranking question. You must be very careful "
                    "about the ordering."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Question: {question_data['question']}\n\n"
                    f"Generated answers (in order, 1st to 5th):\n"
                    f"1. {question_data['answers'][0]}\n"
                    f"2. {question_data['answers'][1]}\n"
                    f"3. {question_data['answers'][2]}\n"
                    f"4. {question_data['answers'][3]}\n"
                    f"5. {question_data['answers'][4]}\n\n"
                    f"Web source data:\n{sources_text}\n\n"
                    "Based on the source data, are these answers correct AND in the "
                    "right order?\n\n"
                    "Respond with ONLY a JSON object:\n"
                    "- \"status\": one of \"VERIFIED\", \"CORRECTED\", or \"UNVERIFIABLE\"\n"
                    "- \"corrected_answers\": (only if CORRECTED) array of 5 answers in "
                    "the correct order\n"
                    "- \"corrected_source\": (only if CORRECTED) the URL of the most "
                    "authoritative source used for correction\n"
                    "- \"reason\": brief explanation of your finding\n\n"
                    "Use VERIFIED if the generated answers match the sources in both "
                    "content and order.\n"
                    "Use CORRECTED if the right answers exist but in a different order, "
                    "or if some answers need to be swapped. Provide the corrected list.\n"
                    "Use UNVERIFIABLE if the source data is insufficient, contradictory, "
                    "or doesn't address the question."
                ),
            },
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )

    try:
        return json.loads(response.choices[0].message.content)
    except (json.JSONDecodeError, IndexError):
        return {"status": "UNVERIFIABLE", "reason": "Failed to parse cross-check response"}


# ---------------------------------------------------------------------------
# Step 2e: Re-verify correction
# ---------------------------------------------------------------------------


def re_verify_correction(llm, search, question_data, corrected_answers):
    """
    When answers were corrected by the cross-check, do a second round of
    verification with a more targeted search to confirm the corrected order.
    """
    # Build a more specific search query focusing on the ordering
    top_two = corrected_answers[:2]
    specific_query = (
        f"{question_data['question']} "
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
                    f"Question: {question_data['question']}\n\n"
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
        temperature=0.0,
        response_format={"type": "json_object"},
    )

    try:
        return json.loads(response.choices[0].message.content)
    except (json.JSONDecodeError, IndexError):
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
    topics = discover_topics(llm, search)

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
        t.get("topic", t.get("suggested_question", "unknown")) for t in topics
    ]
    print(f"Found {len(topics)} candidate topics:")
    for i, t in enumerate(topics):
        print(f"  {i+1}. {t.get('topic', 'N/A')}: {t.get('suggested_question', 'N/A')}")

    # ------------------------------------------------------------------
    # Step 2: Attempt loop
    # ------------------------------------------------------------------
    success = False
    final_entry = None

    for attempt_idx, topic_info in enumerate(topics[:MAX_TOPIC_ATTEMPTS]):
        topic = topic_info.get("topic", "")
        suggested_q = topic_info.get("suggested_question", "")
        attempt_log = {"topic": topic, "status": "pending", "reason": ""}

        print(f"\n--- Attempt {attempt_idx + 1}/{MAX_TOPIC_ATTEMPTS}: {topic} ---")

        # 2a. Similarity check
        print("  Checking similarity...")
        if is_too_similar(llm, topic, suggested_q, previous_summary):
            print("  ❌ Too similar to a previous question. Skipping.")
            attempt_log["status"] = "skipped_similar"
            attempt_log["reason"] = "Too similar to previous question"
            run_log["attempts"].append(attempt_log)
            continue

        # 2b. Generate question
        print("  Generating question...")
        question_data = generate_question(llm, topic, suggested_q)
        if not question_data or "answers" not in question_data or len(question_data.get("answers", [])) != 5:
            print("  ❌ Failed to generate valid question. Skipping.")
            attempt_log["status"] = "generation_failed"
            attempt_log["reason"] = "LLM did not return valid question structure"
            run_log["attempts"].append(attempt_log)
            continue

        print(f"  Question: {question_data['question']}")
        print(f"  Answers: {question_data['answers']}")

        # 2c. Verify via search
        print("  Searching for verification sources...")
        sources = search_for_verification(search, question_data)
        if not sources:
            print("  ❌ No sources found for verification. Skipping.")
            attempt_log["status"] = "no_sources"
            attempt_log["reason"] = "No verification sources found"
            run_log["attempts"].append(attempt_log)
            continue

        print(f"  Found {len(sources)} sources for verification")

        # 2d. Cross-check
        print("  Cross-checking answers against sources...")
        check_result = cross_check(llm, question_data, sources)
        status = check_result.get("status", "UNVERIFIABLE")
        print(f"  Cross-check result: {status}")
        print(f"  Reason: {check_result.get('reason', 'N/A')}")

        final_answers = question_data["answers"]
        source_url = question_data.get("source", "")

        if status == "VERIFIED":
            # Answers confirmed — use as-is
            print("  ✅ Answers verified!")

        elif status == "CORRECTED":
            corrected = check_result.get("corrected_answers", [])
            if len(corrected) != 5:
                print("  ❌ Correction returned invalid number of answers. Skipping.")
                attempt_log["status"] = "correction_invalid"
                attempt_log["reason"] = f"Correction had {len(corrected)} answers instead of 5"
                run_log["attempts"].append(attempt_log)
                continue

            print(f"  Corrected answers: {corrected}")

            # 2e. Re-verify correction
            print("  Re-verifying corrected order...")
            re_verify = re_verify_correction(llm, search, question_data, corrected)
            re_status = re_verify.get("status", "REJECTED")
            print(f"  Re-verification result: {re_status}")
            print(f"  Reason: {re_verify.get('reason', 'N/A')}")

            if re_status == "CONFIRMED":
                print("  ✅ Corrected order confirmed!")
                final_answers = corrected
                source_url = re_verify.get("best_source", source_url)
                if check_result.get("corrected_source"):
                    source_url = check_result["corrected_source"]
            else:
                print("  ❌ Corrected order rejected. Skipping topic.")
                attempt_log["status"] = "correction_rejected"
                attempt_log["reason"] = re_verify.get("reason", "Re-verification failed")
                run_log["attempts"].append(attempt_log)
                continue

        else:
            # UNVERIFIABLE
            print("  ❌ Answers unverifiable. Skipping topic.")
            attempt_log["status"] = "unverifiable"
            attempt_log["reason"] = check_result.get("reason", "Unverifiable")
            run_log["attempts"].append(attempt_log)
            continue

        # If we reach here, we have verified answers
        # Assemble and validate
        print("  Assembling final question entry...")
        final_entry = assemble_question_entry(
            date_str, question_data, final_answers, source_url, next_id
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
