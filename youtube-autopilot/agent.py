#!/usr/bin/env python3
"""
YouTube Autopilot — Idea Agent
--------------------------------
A simple AI assistant that helps you plan better videos.
Uses the same Groq API key already in your .env.
Does NOT touch or run any part of the main pipeline.

Run: python agent.py
"""

import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"
API_KEY = os.getenv("GROQ_API_KEY", "")
NICHE = os.getenv("CHANNEL_NICHE", "interesting facts")

SYSTEM_PROMPT = f"""You are a YouTube growth strategist and content advisor for a faceless educational YouTube channel.
The channel niche is: {NICHE}

You help the channel owner with:
- Brainstorming video topic ideas
- Improving titles for better click-through rate
- Suggesting content series or themes
- Giving honest feedback on ideas
- Recommending upload schedules or strategies

Keep your answers short, practical, and actionable. No fluff.
When listing ideas, give 5 at a time max."""

MENU = """
╔══════════════════════════════════════╗
║       YouTube Autopilot Agent        ║
╠══════════════════════════════════════╣
║  1 - Suggest 5 video topic ideas     ║
║  2 - Improve a title                 ║
║  3 - Brainstorm a content series     ║
║  4 - Rate my idea                    ║
║  5 - What should I upload this week? ║
║  6 - Free chat (ask anything)        ║
║  q - Quit                            ║
╚══════════════════════════════════════╝
"""


def ask_groq(messages: list) -> str:
    if not API_KEY:
        return "❌ GROQ_API_KEY not found in your .env file."
    try:
        resp = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": MODEL, "messages": messages, "temperature": 0.8},
            timeout=30
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"❌ Error: {e}"


def chat(user_message: str, history: list) -> str:
    history.append({"role": "user", "content": user_message})
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
    reply = ask_groq(messages)
    history.append({"role": "assistant", "content": reply})
    return reply


def quick_ask(prompt: str) -> str:
    return ask_groq([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ])


def main():
    if sys.platform == "win32":
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")
        sys.stdout.reconfigure(encoding="utf-8")

    print(f"\n🤖 Agent ready. Your niche: \"{NICHE}\"")
    history = []

    while True:
        print(MENU)
        choice = input("Choose an option: ").strip().lower()

        if choice == "q":
            print("👋 Bye!")
            break

        elif choice == "1":
            print("\n💡 Thinking of ideas...\n")
            reply = quick_ask(f"Give me 5 fresh, specific video topic ideas for a channel about: {NICHE}. Make them curiosity-driven and timeless.")
            print(reply)

        elif choice == "2":
            title = input("\nPaste your current title: ").strip()
            if not title:
                continue
            print("\n✏️  Improving title...\n")
            reply = quick_ask(f"Improve this YouTube title for better CTR. Give 3 alternatives ranked best to worst. Original: \"{title}\"")
            print(reply)

        elif choice == "3":
            theme = input("\nWhat theme or topic area? (or press Enter for your niche): ").strip()
            if not theme:
                theme = NICHE
            print("\n📚 Building series idea...\n")
            reply = quick_ask(f"Design a 5-part YouTube video series about \"{theme}\" for a faceless educational channel. Give each episode a title and one-line description.")
            print(reply)

        elif choice == "4":
            idea = input("\nDescribe your video idea: ").strip()
            if not idea:
                continue
            print("\n🔍 Analyzing idea...\n")
            reply = quick_ask(f"Rate this YouTube video idea out of 10 for a faceless channel. Give: score, what works, what doesn't, and one improvement. Idea: \"{idea}\"")
            print(reply)

        elif choice == "5":
            print("\n📅 Planning this week...\n")
            reply = quick_ask(f"Suggest 3 video topics I should upload this week for a channel about \"{NICHE}\". Consider what's evergreen and what might be trending. Give a title and why for each.")
            print(reply)

        elif choice == "6":
            print("\n💬 Free chat mode (type 'back' to return to menu)\n")
            while True:
                user_input = input("You: ").strip()
                if user_input.lower() in ("back", "exit", "q"):
                    break
                if not user_input:
                    continue
                print("\nAgent:", chat(user_input, history), "\n")

        else:
            print("❓ Invalid choice, try again.")

        input("\n[Press Enter to continue]")


if __name__ == "__main__":
    main()
