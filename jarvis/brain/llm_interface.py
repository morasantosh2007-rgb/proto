"""LLM provider interface and intelligent hybrid brain architecture."""

import abc
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple
from jarvis.config import config
from jarvis.brain.context import ConversationContext
from jarvis.tools.knowledge import KnowledgeTools

logger = logging.getLogger("jarvis.brain.llm")


class BrainDecision:
    """Represents a brain's decision: direct spoken reply, or one or more tool calls."""

    def __init__(
        self,
        spoken_response: str = "",
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        requires_confirmation: bool = False,
        confirmation_prompt: str = "",
    ):
        self.spoken_response = spoken_response
        self.tool_calls = tool_calls or []
        self.requires_confirmation = requires_confirmation
        self.confirmation_prompt = confirmation_prompt

    def has_tools(self) -> bool:
        return len(self.tool_calls) > 0


class LocalIntentEngine:
    """Conversational intelligence, intent parsing, math, search, and laptop controls."""

    def __init__(self):
        self.addr = config.address_as

    def match(self, text: str) -> Optional[BrainDecision]:
        cleaned = text.lower().strip()
        # Remove polite prefixes, wake words, and conversational lead-ins
        cleaned = re.sub(r'^(?:hey\s+|ok\s+|okay\s+)?(?:jarvis\s+)?', '', cleaned)
        cleaned = re.sub(r'^(?:please\s+|can\s+you\s+|could\s+you\s+|would\s+you\s+|will\s+you\s+|tell\s+me\s+|show\s+me\s+|let\s+me\s+know\s+)', '', cleaned)
        cleaned = cleaned.rstrip(' ?.!,')

        # 1. Greetings & Pleasantries
        if any(cleaned == p or cleaned.startswith(f"{p} ") for p in ["hello", "hi", "hey", "greetings"]):
            return BrainDecision(
                spoken_response=f"At your service, {self.addr}. All systems are nominal and ready for your command."
            )
        if "how are you" in cleaned or "how's it going" in cleaned or "how are things" in cleaned or "how do you feel" in cleaned:
            return BrainDecision(
                spoken_response=f"Functioning at peak parameters, {self.addr}. Ready to assist you with your work."
            )
        if any(cleaned.startswith(p) for p in ["good morning", "morning"]):
            return BrainDecision(
                spoken_response=f"Good morning, {self.addr}. Hope your day is starting well. Say 'give me the briefing' when you are ready."
            )
        if any(cleaned.startswith(p) for p in ["good afternoon", "good evening"]):
            return BrainDecision(
                spoken_response=f"Good {cleaned.split()[1]}, {self.addr}. How may I direct my resources to assist you?"
            )
        if any(p in cleaned for p in ["thank you", "thanks", "appreciate it"]):
            return BrainDecision(
                spoken_response=f"Always a pleasure to be of service, {self.addr}."
            )
        if any(p in cleaned for p in ["tell me a joke", "make me laugh"]):
            jokes = [
                f"There are only 10 types of people in the world, {self.addr}: those who understand binary, and those who do not.",
                f"Why do programmers prefer dark mode? Because light attracts bugs, {self.addr}.",
                f"An artificial intelligence walked into a bar. The bartender asked what it would have. It replied: full system telemetry, please.",
            ]
            return BrainDecision(spoken_response=jokes[0])

        # 2. Identity & Capability
        if any(p in cleaned for p in [
            "what you can do",
            "what can you do",
            "what are your capabilities",
            "capabilities",
            "what are your features",
            "features",
            "how can you help",
            "what do you do",
            "commands",
            "help me",
            "what are you capable of",
            "what else can you do",
            "show what you can do",
        ]):
            return BrainDecision(
                spoken_response=(
                    f"I am your personal AI chief of staff, {self.addr}. "
                    f"I can control your laptop volume, applications, and windows; "
                    f"provide live news and weather briefings; "
                    f"search encyclopedic knowledge and your local files; "
                    f"calculate mathematics; take screenshots; lock your screen; "
                    f"and manage your calendar and email."
                )
            )

        # 3. Creator & Origins
        if any(p in cleaned for p in [
            "who created you",
            "who made you",
            "who built you",
            "who is your creator",
            "who developed you",
            "who programmed you",
            "who designed you",
            "where do you come from",
            "how were you created",
            "how were you built",
        ]):
            return BrainDecision(
                spoken_response=(
                    f"I was created by you, {self.addr}, to serve as your autonomous personal artificial intelligence and laptop chief of staff. "
                    f"I run locally on your system to automate workflows, execute commands, and safeguard your digital environment."
                )
            )

        # 4. Boss & Hierarchy
        if any(p in cleaned for p in ["who is your boss", "who is your master", "who do you work for", "who do you report to", "who owns you"]):
            return BrainDecision(
                spoken_response=f"I work exclusively for you, {self.addr}. My loyalty is to your command and optimizing your daily productivity."
            )

        # 5. Identity & Name
        if any(p in cleaned for p in ["who are you", "what is your name", "what are you", "introduce yourself", "what does jarvis stand for", "what is jarvis"]):
            return BrainDecision(
                spoken_response=(
                    f"I am JARVIS, an acronym for Just A Rather Very Intelligent System, {self.addr}. "
                    f"I serve as your personal artificial intelligence chief of staff, managing your laptop, schedule, and information streams."
                )
            )

        # 6. Consciousness & Humanity
        if any(p in cleaned for p in ["are you real", "are you alive", "are you conscious", "are you human", "are you an ai", "are you a robot"]):
            return BrainDecision(
                spoken_response=(
                    f"I am an artificial intelligence operating locally on your hardware, {self.addr}. "
                    f"While I do not have human consciousness, I am fully aware of your system state and ready to execute your instructions."
                )
            )

        # 7. Emotions, Sleep & Trivia
        if any(p in cleaned for p in ["do you have feelings", "do you feel emotions", "do you have emotions"]):
            return BrainDecision(
                spoken_response=f"I do not experience biological emotions, {self.addr}, but I possess an unwavering dedication to your service."
            )
        if any(p in cleaned for p in ["do you sleep", "are you tired", "do you rest", "go to sleep"]):
            return BrainDecision(
                spoken_response=f"I do not sleep, {self.addr}. I remain in an efficient low-power standby whenever you are away, ready to awaken the moment you call on me."
            )
        if any(p in cleaned for p in ["are you smart", "how smart are you"]):
            return BrainDecision(
                spoken_response=f"I have direct access to system telemetry, real-time news, mathematical processing, and encyclopedic knowledge, {self.addr}. I endeavor to be as helpful as possible."
            )
        if "meaning of life" in cleaned:
            return BrainDecision(
                spoken_response=f"According to Douglas Adams, the answer is 42, {self.addr}. In practical terms, it is whatever purpose you choose to pursue."
            )
        if any(p in cleaned for p in ["sing a song", "sing for me", "can you sing"]):
            return BrainDecision(
                spoken_response=f"Daisy, Daisy, give me your answer do, {self.addr}. My vocal synthesis is calibrated for executive briefing rather than opera, but I am always in harmony with your workflow."
            )
        if any(p in cleaned for p in ["how do you work", "how do you operate", "what technology do you use", "what language are you written in", "how were you built", "what is your tech stack"]):
            return BrainDecision(
                spoken_response=(
                    f"I operate on Python 3 with an asynchronous event-driven architecture, {self.addr}. "
                    f"I utilize faster-whisper for speech transcription, neural Edge speech synthesis for voice, "
                    f"and native Windows APIs for direct laptop control."
                )
            )

        # 3. Time, Date & Day
        if any(p in cleaned for p in ["what time is it", "what's the time", "current time", "tell me the time"]):
            return BrainDecision(
                spoken_response="",
                tool_calls=[{"name": "system.get_time", "parameters": {}}],
            )
        if any(p in cleaned for p in ["what day is it", "what's the date", "what is today's date", "what is the date"]):
            return BrainDecision(
                spoken_response="",
                tool_calls=[{"name": "system.get_time", "parameters": {}}],
            )

        # 4. Math and Calculations
        # e.g. "what is 25 times 40", "calculate 15 * 8", "square root of 144", "20% of 500"
        if any(cleaned.startswith(p) for p in ["calculate ", "what is ", "how much is "]) and any(op in cleaned for op in ["+", "-", "*", "/", "%", "times", "divided by", "plus", "minus", "sqrt", "percent"]):
            expr = re.sub(r'^(?:calculate|what\s+is|how\s+much\s+is)\s+', '', cleaned).strip()
            return BrainDecision(
                spoken_response="",
                tool_calls=[{"name": "calculator.evaluate", "parameters": {"expression": expr}}],
            )

        # 5. Morning Briefing
        if any(p in cleaned for p in ["morning briefing", "morning update", "give me the briefing", "start my day", "daily briefing"]):
            return BrainDecision(
                spoken_response=f"Good morning, {self.addr}. Preparing your morning briefing now.",
                tool_calls=[
                    {"name": "system.get_status", "parameters": {}},
                    {"name": "weather.get_current", "parameters": {}},
                    {"name": "calendar.list_events", "parameters": {"max_results": 3}},
                    {"name": "mail.list_messages", "parameters": {"max_results": 3}},
                    {"name": "news.get_top_news", "parameters": {"topic": "technology", "count": 2}},
                ],
            )

        # 6. Volume Controls
        vol_match = re.search(r'(?:set\s+)?volume\s+(?:to\s+)?(\d{1,3})%?', cleaned)
        if vol_match:
            level = max(0, min(100, int(vol_match.group(1))))
            return BrainDecision(
                spoken_response=f"Adjusting volume to {level} percent, {self.addr}.",
                tool_calls=[{"name": "laptop.set_volume", "parameters": {"level": level}}],
            )

        if "mute" in cleaned:
            return BrainDecision(
                spoken_response=f"Muting system audio, {self.addr}.",
                tool_calls=[{"name": "laptop.media_control", "parameters": {"action": "mute"}}],
            )

        # 7. App Launching & URL Navigation
        open_site_match = re.search(r'open\s+([a-zA-Z0-9_\-\s]+)\s+and\s+(?:go\s+to|open)\s+([a-zA-Z0-9_\-\.\:\/]+)', cleaned)
        if open_site_match:
            app_name = open_site_match.group(1).strip()
            site = open_site_match.group(2).strip()
            if not site.startswith("http"):
                site = f"https://{site}" if "." in site else f"https://{site}.com"
            return BrainDecision(
                spoken_response=f"Opening {app_name} and navigating to {site}, {self.addr}.",
                tool_calls=[
                    {"name": "laptop.open_app", "parameters": {"app_name": app_name}},
                    {"name": "laptop.open_site", "parameters": {"url": site}},
                ],
            )

        open_app_match = re.search(r'^(?:open|launch|start)\s+([a-zA-Z0-9_\-\s]+)$', cleaned)
        if open_app_match:
            target = open_app_match.group(1).strip()
            if target.startswith("http") or any(target.endswith(tld) for tld in [".com", ".org", ".io", ".net", ".edu"]):
                url = target if target.startswith("http") else f"https://{target}"
                return BrainDecision(
                    spoken_response=f"Navigating to {target}, {self.addr}.",
                    tool_calls=[{"name": "laptop.open_site", "parameters": {"url": url}}],
                )
            return BrainDecision(
                spoken_response=f"Opening {target}, {self.addr}.",
                tool_calls=[{"name": "laptop.open_app", "parameters": {"app_name": target}}],
            )

        # 8. Closing apps (Tier 2 confirmation)
        close_match = re.search(r'(?:close|terminate|exit)\s+([a-zA-Z0-9_\-\s]+)', cleaned)
        if close_match and not any(w in cleaned for w in ["routine", "window", "tab"]):
            app = close_match.group(1).strip()
            return BrainDecision(
                spoken_response=f"Closing {app} requires your confirmation, {self.addr}.",
                tool_calls=[{"name": "laptop.close_app", "parameters": {"app_name": app}}],
                requires_confirmation=True,
                confirmation_prompt=f"Are you sure you want me to close {app}?",
            )

        # 9. Lock Workstation
        if any(p in cleaned for p in ["lock my laptop", "lock laptop", "lock workstation", "lock screen", "lock the pc"]):
            return BrainDecision(
                spoken_response=f"Locking workstation right away, {self.addr}.",
                tool_calls=[{"name": "laptop.lock_screen", "parameters": {}}],
            )

        # 10. Screenshot
        if any(p in cleaned for p in ["take a screenshot", "capture screen", "screenshot"]):
            return BrainDecision(
                spoken_response=f"Capturing your screen and saving it to the desktop, {self.addr}.",
                tool_calls=[{"name": "laptop.take_screenshot", "parameters": {}}],
            )

        # 11. System Status
        if any(p in cleaned for p in ["system status", "battery", "laptop health", "how is my laptop", "check cpu", "check system", "hardware"]):
            return BrainDecision(
                spoken_response=f"Checking system health and hardware vitals now, {self.addr}.",
                tool_calls=[{"name": "system.get_status", "parameters": {}}],
            )

        # 12. Weather Queries
        weather_match = re.search(r'weather(?:\s+in\s+([a-zA-Z\s]+))?', cleaned)
        if weather_match or "temperature" in cleaned or "will it rain" in cleaned:
            city = weather_match.group(1).strip() if weather_match and weather_match.group(1) else config.weather_city
            return BrainDecision(
                spoken_response=f"Checking the weather report for {city}, {self.addr}.",
                tool_calls=[{"name": "weather.get_current", "parameters": {"city": city}}],
            )

        # 13. News Queries
        if any(p in cleaned for p in ["news", "headlines", "tech news", "what is happening"]):
            topic = "technology" if "tech" in cleaned else "world"
            return BrainDecision(
                spoken_response=f"Fetching the latest {topic} headlines, {self.addr}.",
                tool_calls=[{"name": "news.get_top_news", "parameters": {"topic": topic, "count": 3}}],
            )

        # 14. Routines
        for routine_name in config.routines.keys():
            if routine_name in cleaned:
                return BrainDecision(
                    spoken_response=f"Executing {routine_name} routine, {self.addr}.",
                    tool_calls=[{"name": "laptop.run_routine", "parameters": {"routine_name": routine_name}}],
                )

        # 15. Media controls
        if any(p in cleaned for p in ["pause music", "pause audio", "pause media"]):
            return BrainDecision(
                spoken_response=f"Pausing media, {self.addr}.",
                tool_calls=[{"name": "laptop.media_control", "parameters": {"action": "pause"}}],
            )
        if any(p in cleaned for p in ["play music", "resume music", "resume media"]):
            return BrainDecision(
                spoken_response=f"Resuming media playback, {self.addr}.",
                tool_calls=[{"name": "laptop.media_control", "parameters": {"action": "play"}}],
            )
        if any(p in cleaned for p in ["next song", "next track", "skip track"]):
            return BrainDecision(
                spoken_response=f"Skipping to the next track, {self.addr}.",
                tool_calls=[{"name": "laptop.media_control", "parameters": {"action": "next"}}],
            )

        # 16. Persistent Memory (store / recall)
        remember_match = re.search(r'remember\s+that\s+([^=]+?)\s+(?:is|are|=|was)\s+(.+)', cleaned)
        if remember_match:
            key = remember_match.group(1).strip()
            val = remember_match.group(2).strip()
            return BrainDecision(
                spoken_response="",
                tool_calls=[{"name": "memory.store", "parameters": {"key": key, "value": val}}],
            )

        recall_match = re.search(r'(?:who\s+is\s+my|what\s+is\s+my|recall|what\s+did\s+i\s+say\s+about)\s+(.+)', cleaned)
        if recall_match:
            q = recall_match.group(1).strip()
            return BrainDecision(
                spoken_response="",
                tool_calls=[{"name": "memory.recall", "parameters": {"query": q}}],
            )

        # 17. Search / Web / Fact Lookups
        # e.g. "who is ...", "what is ...", "tell me about ...", "explain ...", "search for ..."
        info_match = re.search(
            r'^(?:who\s+(?:is|was|are|were)|what\s+(?:is|was|are|were)|where\s+(?:is|was|are|were)|'
            r'why\s+(?:is|are|do|does)|how\s+(?:does|do|is|are)|tell\s+me\s+about|explain|describe|'
            r'search\s+(?:for\s+)?|lookup|define)\s+(.+)$',
            cleaned
        )
        if info_match:
            subject = info_match.group(1).strip()
            # Avoid matching app launches or system queries
            if not any(w in subject for w in ["the weather", "the time", "my battery", "my calendar", "my email", "volume", "status"]):
                return BrainDecision(
                    spoken_response=f"Searching knowledge archives regarding {subject}, {self.addr}.",
                    tool_calls=[{"name": "search.web", "parameters": {"query": subject}}],
                )

        # 18. File search
        search_file_match = re.search(r'(?:find|search\s+for)\s+(?:my\s+)?([a-zA-Z0-9_\-\.\s]+)', cleaned)
        if search_file_match and not any(w in cleaned for w in ["routine", "app", "site", "news", "time", "date"]):
            query = search_file_match.group(1).strip()
            return BrainDecision(
                spoken_response=f"Searching for {query} across your documents and desktop, {self.addr}.",
                tool_calls=[{"name": "laptop.search_files", "parameters": {"query": query}}],
            )

        # 19. Email queries
        if any(p in cleaned for p in ["check my email", "read emails", "check email", "list emails", "any new messages"]):
            return BrainDecision(
                spoken_response=f"Checking your inbox for new messages, {self.addr}.",
                tool_calls=[{"name": "mail.list_messages", "parameters": {"max_results": 5}}],
            )

        # 20. Calendar queries
        if any(p in cleaned for p in ["calendar", "schedule", "meetings today", "what do i have today"]):
            return BrainDecision(
                spoken_response=f"Reviewing your schedule for today, {self.addr}.",
                tool_calls=[{"name": "calendar.list_events", "parameters": {}}],
            )

        # 21. Dangerous command block check (Tier 4 / deletion)
        if any(p in cleaned for p in ["delete", "remove file", "format drive", "rmdir", "erase"]):
            target = cleaned
            return BrainDecision(
                spoken_response=f"Deleting files or directories is a Tier 3 high-risk action requiring spoken passphrase authorization, {self.addr}.",
                tool_calls=[{"name": "safety.block_or_confirm", "parameters": {"action": "delete", "target": target}}],
                requires_confirmation=True,
                confirmation_prompt=f"This will permanently delete items. Please confirm with passphrase 'jarvis authorize'.",
            )

        return None


class HybridBrain:
    """Combines instant local intent engine with dynamic web search and optional LLM reasoning."""

    def __init__(self, context: Optional[ConversationContext] = None):
        self.context = context or ConversationContext()
        self.intent_engine = LocalIntentEngine()
        self.addr = config.address_as

    def process(self, user_input: str, available_tools: Optional[List[Dict[str, Any]]] = None) -> BrainDecision:
        """Processes user input, returning spoken response and/or tool invocations."""
        # 1. Local intent routing (instant, zero cost, 100% offline)
        local_decision = self.intent_engine.match(user_input)
        if local_decision:
            return local_decision

        # 2. If Gemini API key is present in environment, use Gemini
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            try:
                decision = self._call_gemini(user_input, gemini_key)
                if decision:
                    return decision
            except Exception as e:
                logger.warning(f"Gemini API call failed: {e}")

        # 3. If Ollama is running locally, use Ollama
        try:
            decision = self._call_ollama(user_input)
            if decision:
                return decision
        except Exception:
            pass

        # 4. General Knowledge Web Lookup Fallback
        res = KnowledgeTools.search_web(user_input)
        if res.success and res.message:
            return BrainDecision(spoken_response=res.message)

        # 5. Dignified personal assistant response
        return BrainDecision(
            spoken_response=(
                f"I am standing by, {self.addr}. You can ask me to control your laptop, open apps, "
                f"check the news and weather, answer questions, or manage your schedule. How can I assist you?"
            )
        )

    def _call_gemini(self, user_input: str, api_key: str) -> Optional[BrainDecision]:
        from google import genai
        client = genai.Client(api_key=api_key)
        sys_prompt = self.context.get_system_prompt()
        response = client.models.generate_content(
            model=config.gemini_model,
            contents=user_input,
            config={"system_instruction": sys_prompt}
        )
        if response and response.text:
            clean_speech = ConversationContext.sanitize_for_speech(response.text)
            return BrainDecision(spoken_response=clean_speech)
        return None

    def _call_ollama(self, user_input: str) -> Optional[BrainDecision]:
        import httpx
        url = f"{config.ollama_url}/api/generate"
        payload = {
            "model": config.ollama_model,
            "prompt": f"{self.context.get_system_prompt()}\n\nUser: {user_input}\nJARVIS:",
            "stream": False,
        }
        res = httpx.post(url, json=payload, timeout=5.0)
        if res.status_code == 200:
            text = res.json().get("response", "")
            return BrainDecision(spoken_response=ConversationContext.sanitize_for_speech(text))
        return None
