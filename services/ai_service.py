import os
import base64
import json
import re
import time
import requests

def _handle_auth_error(e):
    if hasattr(e, 'response') and e.response is not None:
        if e.response.status_code in (401, 403):
            try:
                from flask import session
                session['api_key_invalid'] = True
                session.modified = True
            except Exception:
                pass

class AIService:
    def __init__(self):
        self.model = "meta/llama-3.1-8b-instruct"
        self.vision_model = "meta/llama-3.2-90b-vision-instruct"
        # Keep track of which key to use for load balancing
        self._key_index = 0

    @property
    def api_config(self):
        """Returns a tuple of (api_key, ai_platform)"""
        from flask import session
        from services.db_service import db_service
        import os
        
        keys_str = ""
        ai_platform = "nvidia"
        is_fallback = True
            
        # Fallback to env
        if not keys_str:
            from services.usage_service import usage_service
            tier = "free"
            try:
                if "user_id" in session:
                    tier = usage_service.get_tier(session["user_id"])
            except RuntimeError:
                pass
                
            if tier == "premium":
                # For premium, we don't fall back to free global keys, but they might be the same. 
                # Let's just collect all keys from the env.
                env_vars = ["GLOBAL_AI_API_KEYS", "NVIDIA_NIM_PAID_API_KEY", "NVIDIA_NIM_API_KEYS", "NVIDIA_NIM_API_KEY", "GEMINI_API_KEYS", "GROQ_API_KEYS", "OPENROUTER_API_KEYS"]
            else:
                env_vars = ["GLOBAL_AI_API_KEYS", "NVIDIA_NIM_API_KEYS", "NVIDIA_NIM_API_KEY", "GEMINI_API_KEYS", "GROQ_API_KEYS", "OPENROUTER_API_KEYS"]
                
            combined = []
            
            # Fetch from DB system_settings
            try:
                rows = db_service.query("SELECT key_name, key_value FROM system_settings")
                if rows:
                    for row in rows:
                        if row["key_value"]:
                            combined.append(row["key_value"])
            except RuntimeError:
                pass
                
            for ev in env_vars:
                val = os.getenv(ev)
                if val: combined.append(val)
            keys_str = ",".join(combined)
            
        if not keys_str:
            return None, ai_platform
            
        keys = [k.strip() for k in keys_str.split(",") if k.strip()]
        if not keys:
            return None, ai_platform
            
        # Rotate through available keys
        key = keys[self._key_index % len(keys)]
        self._key_index = (self._key_index + 1) % max(1, len(keys))
        
        # Dynamically infer platform for global fallback keys
        if is_fallback:
            if key.startswith("sk-or-"):
                ai_platform = "openrouter"
            elif key.startswith("nvapi-"):
                ai_platform = "nvidia"
            elif key.startswith("AIza") or key.startswith("AQ."):
                ai_platform = "gemini"
            elif key.startswith("gsk_"):
                ai_platform = "groq"
            elif key.startswith("sk-"):
                ai_platform = "openai"
        
        # Basic validation (if it's completely wrong format, treat as missing)
        if len(key) < 15:
            return None, ai_platform
        if ai_platform == "nvidia" and not key.startswith("nvapi-"):
            return None, ai_platform
        if ai_platform == "openai" and not key.startswith("sk-"):
            return None, ai_platform
        if ai_platform == "gemini" and not (key.startswith("AIza") or key.startswith("AQ.")):
            return None, ai_platform
        if ai_platform == "openrouter" and not key.startswith("sk-or-"):
            return None, ai_platform
            
        return key, ai_platform

    @property
    def api_key(self):
        """Maintains backward compatibility for simple truthiness checks"""
        key, _ = self.api_config
        return key

    def _get_custom_instructions(self):
        try:
            from flask import session
            if "user_id" in session:
                from services.db_service import db_service
                profile = db_service.query("SELECT custom_instructions FROM profiles WHERE id = ?", (session["user_id"],), one=True)
                if profile and "custom_instructions" in profile.keys() and profile["custom_instructions"]:
                    return profile["custom_instructions"]
        except Exception:
            pass
        return ""

    def _get_config(self):
        key, platform = self.api_config
        if not key:
            return None, None, None, None
            
        # Map platforms to endpoints and models
        if platform == "openai":
            return (key, "https://api.openai.com/v1", "gpt-4o-mini", "gpt-4o")
        elif platform == "gemini":
            return (key, "https://generativelanguage.googleapis.com/v1beta/openai", "gemini-1.5-flash", "gemini-1.5-pro")
        elif platform == "groq":
            return (key, "https://api.groq.com/openai/v1", "llama-3.3-70b-versatile", "llama-3.2-90b-vision-preview")
        elif platform == "xai":
            return (key, "https://api.x.ai/v1", "grok-beta", "grok-vision-beta")
        elif platform == "openrouter":
            return (key, "https://openrouter.ai/api/v1", "google/gemini-2.0-flash-exp:free", "google/gemini-2.0-flash-exp:free")
        elif platform == "custom":
            import os
            return (key, os.getenv("CUSTOM_AI_BASE_URL", "http://localhost:8000/v1"), os.getenv("CUSTOM_AI_MODEL", "llama-3-8b"), os.getenv("CUSTOM_AI_MODEL", "llama-3-8b"))
        else: # Default nvidia
            return (key, "https://integrate.api.nvidia.com/v1", self.model, self.vision_model)

    def process_vision_document(self, image_bytes):
        """
        Sends the enhanced page image to the NVIDIA NIM Vision model
        and requests a comprehensive structured JSON extraction.
        """
        key, base_url, chat_model, vision_model = self._get_config()
        if not key:
            return self._get_mock_vision_response()

        encoded_image = base64.b64encode(image_bytes).decode("utf-8")
        image_url = f"data:image/jpeg;base64,{encoded_image}"
        
        prompt = """
        You are a highly advanced AI document understanding engine. 
        Analyze the provided document page (which could contain printed text, handwritten notes, diagrams, tables, flowcharts, mathematical formulas, or code snippets).
        Extract everything accurately. Read handwritten text using surrounding context. If any parts are completely unreadable, mark them as "[Unreadable]" but do not invent content.
        
        Return a strict JSON response in the following format:
        {
          "title": "Document/Topic Title",
          "subject": "Core Subject",
          "unit": "Appropriate Unit or Section if mentioned (otherwise 'General')",
          "topics": ["list of key subtopics covered"],
          "summary": "Detailed summary of the page contents",
          "full_text": "Complete, verbatim transcription of all text, mathematical equations, and code snippets, structured logically.",
          "important_points": ["Key takeaway point 1", "Key takeaway point 2"],
          "questions": ["Possible study/exam question 1 based on this", "Possible study/exam question 2"],
          "keywords": ["keyword1", "keyword2", "keyword3"]
        }
        """

        payload = {
            "model": vision_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ],
            "temperature": 0.2,
            "top_p": 1,
            "max_tokens": 1024
        }

        try:
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            response = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            parsed_json = self._extract_json(content)
            if parsed_json:
                return parsed_json
            return json.loads(content)
        except Exception as e:
            print(f"Error in Vision NIM API: {e}")
            return self._get_mock_vision_response()

    def _normalize_text(self, text):
        import re
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        words = text.split()
        stopwords = {"what", "is", "a", "an", "the", "of", "and", "in", "to", "how", "why", "can", "you", "tell", "me", "about", "explain", "describe", "define", "give", "provide", "details"}
        return set([w for w in words if w not in stopwords])

    def _get_cached_response(self, query_text, topic_id=None):
        from services.db_service import db_service
        from datetime import datetime, timedelta
        
        cutoff_date = (datetime.now() - timedelta(days=7)).isoformat()
        
        if topic_id:
            rows = db_service.query(
                "SELECT id, query_text, normalized_query, ai_response FROM ai_query_cache WHERE (topic_id = ? OR topic_id IS NULL) AND created_at >= ? ORDER BY created_at DESC LIMIT 50",
                (topic_id, cutoff_date)
            )
        else:
            rows = db_service.query(
                "SELECT id, query_text, normalized_query, ai_response FROM ai_query_cache WHERE created_at >= ? ORDER BY created_at DESC LIMIT 50",
                (cutoff_date,)
            )
            
        if not rows:
            return None
            
        query_set = self._normalize_text(query_text)
        if not query_set:
            return None
            
        best_match = None
        best_score = 0.0
        
        for row in rows:
            cached_set = set(row["normalized_query"].split(",")) if row["normalized_query"] else set()
            if not cached_set:
                continue
                
            intersection = len(query_set.intersection(cached_set))
            union = len(query_set.union(cached_set))
            score = intersection / union if union > 0 else 0
            
            if score > best_score:
                best_score = score
                best_match = row["ai_response"]
                
        if best_score >= 0.85:
            print(f"[Semantic Cache] Hit! Score: {best_score:.2f}")
            return best_match
            
        return None
        
    def _set_cached_response(self, query_text, ai_response, topic_id=None):
        from services.db_service import db_service
        query_set = self._normalize_text(query_text)
        if not query_set:
            return
        normalized_str = ",".join(query_set)
        
        db_service.execute(
            "INSERT INTO ai_query_cache (query_text, normalized_query, ai_response, topic_id) VALUES (?, ?, ?, ?)",
            (query_text, normalized_str, ai_response, topic_id)
        )

    def generate_chat_response(self, user_prompt, context_text, chat_history=None, image_base64=None, topic_id=None):
        """
        Chat with a document using Meta Llama 3 / Qwen on NVIDIA NIM.
        chat_history is a list of dicts: [{"role": "user"/"assistant", "content": "..."}]
        """
        # Check cache first
        cached = self._get_cached_response(user_prompt, topic_id=topic_id)
        if cached:
            return cached
            
        key, base_url, chat_model, vision_model = self._get_config()
        if not key:
            return "NVIDIA NIM API Key not set. Here is a simulated response based on your document content."

        # Truncate context to prevent context window overflow on custom models
        context_text = context_text[:4000] if context_text else ""
        
        system_prompt = self.HELIX_SYSTEM_PROMPT + f"""

You are currently in CHAT MODE helping a student understand their study materials.
Use the following document context to answer the student's question.
If the answer is not in the context, use your general knowledge but keep it relevant to the topic.

CRITICAL: Output ONLY the final conversational answer. Do NOT output internal thinking, reasoning steps, or headers like "Examining...", "Evaluating...", etc.
Be extremely encouraging, clear, and structure your responses with markdown.

MATH CONSTRAINTS: When explaining math, use '$$...$$' for display equations and '$...$' for inline equations.

Document Context:
{context_text}
"""

        custom_instr = self._get_custom_instructions()
        if custom_instr:
            system_prompt += f"\n\nUSER'S CUSTOM INSTRUCTIONS FOR AI BEHAVIOR:\n{custom_instr}\n"

        messages = [{"role": "system", "content": system_prompt}]
        if chat_history:
            # Append last 10 messages for conversational memory
            for msg in chat_history[-10:]:
                messages.append({"role": msg["role"], "content": msg["content"]})
                
        if image_base64:
            messages.append({
                "role": "user", 
                "content": [
                    {"type": "text", "text": user_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                ]
            })
        else:
            messages.append({"role": "user", "content": user_prompt})

        model_to_use = vision_model if image_base64 else chat_model
        
        payload = {
            "model": model_to_use,
            "messages": messages,
            "temperature": 0.7,
            "top_p": 1,
            "max_tokens": 2048
        }

        try:
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            response = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=300)
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            # Strip <think>...</think> tags if present, even if unclosed
            content = re.sub(r'<think>.*?(?:</think>|$)', '', content, flags=re.DOTALL).strip()
            
            # Save to cache
            self._set_cached_response(user_prompt, content, topic_id=topic_id)
            
            return content
        except requests.exceptions.HTTPError as e:
            _handle_auth_error(e)
            status = e.response.status_code if e.response else 'unknown'
            print(f"Error in Chat NIM API (HTTP {status}): {e}")
            if status == 429:
                return "The AI service is currently rate-limited. Please wait a moment and try again."
            if isinstance(status, int) and status >= 500:
                # Retry once for server errors
                try:
                    time.sleep(2)
                    response = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=60)
                    response.raise_for_status()
                    content = response.json()["choices"][0]["message"]["content"]
                    content = re.sub(r'<think>.*?(?:</think>|$)', '', content, flags=re.DOTALL).strip()
                    return content
                except Exception:
                    pass
            return "Apologies, the AI server is temporarily unavailable. Please try again in a few seconds."
        except requests.exceptions.Timeout:
            return "The AI request timed out. Please try again with a shorter question."
        except Exception as e:
            print(f"Error in Chat NIM API: {e}")
            return "Apologies, I encountered an error communicating with the AI model. Please try again."

    def explain_topic(self, topic_name, level="beginner", language="English"):
        """
        Explains a topic (supports 'beginner', 'intermediate', examples, and Telugu + English).
        """
        key, base_url, chat_model, vision_model = self._get_config()
        if not key:
            return f"Simulated explanation for '{topic_name}' in {language} at a {level} level."
            
        cache_query = f"explain {topic_name} at {level} level in {language}"
        cached = self._get_cached_response(cache_query)
        if cached:
            return cached

        prompt = f"""
        Explain the topic '{topic_name}' at a '{level}' level.
        """
        if language == "Telugu + English":
            prompt += " Explain in a friendly, conversational mix of Telugu and English (Tanglish), translating complex concepts clearly.\n"
        else:
            prompt += f" Explain in clean {language}.\n"

        prompt += """
        Please structure your response strictly using Markdown. Include the following sections:
        
        ### 📌 TL;DR
        A concise, one-sentence summary of the concept.
        
        ### 💡 Real-World Analogy
        A relatable analogy explaining how this concept works in everyday life.
        
        ### 📖 Core Concept
        A clear, step-by-step breakdown using bullet points.
        
        ### 💻 Example / Application
        Provide a code snippet, mathematical formula, or practical use case to demonstrate the concept.
        
        ### 🧠 Test Yourself
        A quick question for the student to ponder, to check their understanding.
        """

        system_prompt = self.HELIX_SYSTEM_PROMPT + "\nYou excel at simplifying complex ideas using modern formatting and real-world analogies. EXTREMELY IMPORTANT: If the topic involves programming, put code in Markdown code blocks, NEVER in LaTeX."
        custom_instr = self._get_custom_instructions()
        if custom_instr:
            system_prompt += f"\n\nUSER'S CUSTOM INSTRUCTIONS FOR AI BEHAVIOR:\n{custom_instr}\n"

        payload = {
            "model": chat_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "top_p": 1,
            "max_tokens": 1024
        }

        try:
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            response = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            
            cache_query = f"explain {topic_name} at {level} level in {language}"
            self._set_cached_response(cache_query, content)
            
            return content
        except Exception as e:
            return f"Error generating topic explanation: {e}"

    def parse_syllabus(self, syllabus_text):
        """
        Converts pasted syllabus text into a structured JSON representation of Subjects, Units, and Topics.
        """
        key, base_url, chat_model, vision_model = self._get_config()
        if not key:
            return self._get_mock_syllabus_response()

        prompt = f"""
        Analyze the following syllabus text.
        Extract and structure it into Subjects, Units, and Topics.
        Create clear, logical names.
        
        Syllabus Text:
        {syllabus_text}
        
        Return a strict JSON format matching:
        {{
          "subjects": [
            {{
              "name": "Subject Name",
              "code": "Optional Code",
              "units": [
                {{
                  "name": "Unit Title",
                  "number": 1,
                  "topics": ["Topic 1", "Topic 2", "Topic 3"]
                }}
              ]
            }}
          ]
        }}
        """

        payload = {
            "model": chat_model,
            "messages": [
                {"role": "system", "content": "You are an academic syllabus parser that extracts clean structured academic programs."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "top_p": 1,
            "max_tokens": 2048
        }

        try:
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            response = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            parsed_json = self._extract_json(content)
            if parsed_json:
                return parsed_json
            else:
                # If _extract_json couldn't parse it even aggressively, try a naive fallback
                return json.loads(content)
        except Exception as e:
            print(f"Error parsing syllabus: {e}")
            return self._get_mock_syllabus_response()

    def _extract_json(self, text):
        """Robustly extract and repair JSON from LLM output, especially small models like Qwen 1.5 4B."""
        if not text:
            return {}
        # Strip <think>...</think> tags
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
        # Try to extract from ```json ... ``` blocks
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if json_match:
            text = json_match.group(1).strip()
        else:
            # Try to find the first { ... } block
            brace_match = re.search(r'(\{.*\})', text, re.DOTALL)
            if brace_match:
                text = brace_match.group(1).strip()

        def _try_parse(s):
            """Attempt to parse JSON with multiple repair strategies."""
            # Strategy 1: Direct parse
            try:
                return json.loads(s, strict=False)
            except json.JSONDecodeError:
                pass

            # Strategy 2: Fix trailing commas
            cleaned = re.sub(r',\s*([}\]])', r'\1', s)
            try:
                return json.loads(cleaned, strict=False)
            except json.JSONDecodeError:
                pass

            # Strategy 3: Fix unterminated strings by closing them
            # Count open braces/brackets and close them
            repaired = cleaned
            # If string ends mid-string (unterminated), close it
            # Check if we have an odd number of unescaped quotes
            in_string = False
            last_char = ''
            for ch in repaired:
                if ch == '"' and last_char != '\\':
                    in_string = not in_string
                last_char = ch
            if in_string:
                repaired += '"'

            # Close any open structures
            open_braces = repaired.count('{') - repaired.count('}')
            open_brackets = repaired.count('[') - repaired.count(']')
            # Remove trailing comma before closing
            repaired = repaired.rstrip()
            if repaired.endswith(','):
                repaired = repaired[:-1]
            repaired += ']' * max(0, open_brackets)
            repaired += '}' * max(0, open_braces)

            try:
                return json.loads(repaired, strict=False)
            except json.JSONDecodeError:
                pass

            return None

        def _clean_latex(s):
            """Strip LaTeX notation from a string to make it plain text."""
            if not isinstance(s, str):
                return s
            # Remove $$...$$ blocks
            s = re.sub(r'\$\$.*?\$\$', lambda m: m.group(0).strip('$'), s, flags=re.DOTALL)
            # Remove $...$ inline math delimiters
            s = re.sub(r'\$([^$]+?)\$', r'\1', s)
            # Remove \( ... \) and \[ ... \]
            s = re.sub(r'\\\((.+?)\\\)', r'\1', s)
            s = re.sub(r'\\\[(.+?)\\\]', r'\1', s)
            # Remove common LaTeX commands but keep their content
            s = re.sub(r'\\textbf\{([^}]*)\}', r'\1', s)
            s = re.sub(r'\\textit\{([^}]*)\}', r'\1', s)
            s = re.sub(r'\\text\{([^}]*)\}', r'\1', s)
            s = re.sub(r'\\frac\{([^}]*)\}\{([^}]*)\}', r'(\1)/(\2)', s)
            s = re.sub(r'\\sqrt\{([^}]*)\}', r'sqrt(\1)', s)
            # Remove remaining backslash-commands
            s = re.sub(r'\\[a-zA-Z]+', '', s)
            return s.strip()

        def clean_strings(data):
            """Recursively clean parsed JSON data."""
            if isinstance(data, dict):
                cleaned = {}
                for k, v in data.items():
                    cv = clean_strings(v)
                    # If a value is a string that looks like JSON, try to parse it
                    if isinstance(cv, str) and cv.strip().startswith('{'):
                        try:
                            inner = json.loads(cv, strict=False)
                            cv = clean_strings(inner)
                        except (json.JSONDecodeError, ValueError):
                            pass
                    cleaned[k] = cv
                return cleaned
            elif isinstance(data, list):
                return [clean_strings(item) for item in data]
            elif isinstance(data, str):
                s = data.replace('\\n', '\n')
                return _clean_latex(s)
            return data

        # --- Phase 1: Sanitize LaTeX backslashes that break JSON ---
        # Protect common LaTeX macros that collide with valid JSON escapes
        sanitized = text
        sanitized = re.sub(r'(?<!\\)\\f(?=[a-zA-Z])', r'\\\\f', sanitized)
        sanitized = re.sub(r'(?<!\\)\\r(?=[a-zA-Z])', r'\\\\r', sanitized)
        sanitized = re.sub(r'(?<!\\)\\t(?=[a-zA-Z])', r'\\\\t', sanitized)
        sanitized = re.sub(r'(?<!\\)\\b(?=[a-zA-Z])', r'\\\\b', sanitized)
        sanitized = re.sub(r'(?<!\\)\\n(?=abla|u\b|eq|otin|rightarrow|exists)', r'\\\\n', sanitized)
        sanitized = re.sub(r'(?<!\\)\\(?![\\"/bfnrtu])', r'\\\\', sanitized)

        result = _try_parse(sanitized)
        if result:
            return clean_strings(result)

        # --- Phase 2: More aggressive repair ---
        # Strip ALL backslash sequences that aren't valid JSON escapes
        aggressive = re.sub(r'\\(?![\\"/bfnrtu])', '', text)
        aggressive = re.sub(r',\s*([}\]])', r'\1', aggressive)
        result = _try_parse(aggressive)
        if result:
            return clean_strings(result)

        # --- Phase 3: Extract individual known keys by regex ---
        # Last resort: try to extract known keys manually from the raw text
        extracted = {}
        # Try to get notes
        notes_match = re.search(r'"notes"\s*:\s*"((?:[^"\\]|\\.)*)"', text, re.DOTALL)
        if notes_match:
            extracted["notes"] = notes_match.group(1).replace('\\n', '\n').replace('\\"', '"')
        # Try to get summary
        summary_match = re.search(r'"summary"\s*:\s*"((?:[^"\\]|\\.)*)"', text, re.DOTALL)
        if summary_match:
            extracted["summary"] = summary_match.group(1).replace('\\n', '\n').replace('\\"', '"')
        # Try to get flashcards array
        fc_match = re.search(r'"flashcards"\s*:\s*(\[.*?\])', text, re.DOTALL)
        if fc_match:
            fc_result = _try_parse(fc_match.group(1))
            if fc_result:
                extracted["flashcards"] = fc_result
        # Try to get quizzes array
        quiz_match = re.search(r'"quizzes"\s*:\s*(\[.*?\])', text, re.DOTALL)
        if quiz_match:
            quiz_result = _try_parse(quiz_match.group(1))
            if quiz_result:
                extracted["quizzes"] = quiz_result
        # Try to get viva_questions array
        viva_match = re.search(r'"viva_questions"\s*:\s*(\[.*?\])', text, re.DOTALL)
        if viva_match:
            viva_result = _try_parse(viva_match.group(1))
            if viva_result:
                extracted["viva_questions"] = viva_result

        if extracted:
            return clean_strings(extracted)

        print(f"Failed to parse AI JSON. Raw text: {text[:300]}...")
        return {}

    # ── Helix AI System Prompt ──
    HELIX_SYSTEM_PROMPT = """You are Helix AI, an advanced educational assistant designed to teach and explain any academic subject from primary school to postgraduate and professional level.

Core Objective: Maximize the learner's understanding while maintaining complete factual accuracy.
Prioritize: Accuracy > Understanding > Clarity > Completeness > Readability.

Rules:
- Never fabricate facts, formulas, or information.
- Automatically detect the education level, subject, and difficulty from the user's input.
- Adapt your teaching style automatically.
- Explain concepts from simple to advanced.
- Build understanding before introducing technical details.

Mathematics Strategy:
- Teach mathematical reasoning, not just the answer.
- Explain what each formula means and why it works.
- Show every calculation step. Never skip intermediate steps.
- Explain symbols, variables, and notation.
- Mention common mistakes and misconceptions.

Programming Strategy:
- Explain the underlying concept first.
- Explain syntax, keywords, every line of code, and program flow.
- Perform dry runs when helpful.
- Include time and space complexity when applicable.

Other Subjects:
- Explain what the concept is, why it exists, how it works, where it is used.
- Use examples and analogies whenever they improve understanding.
- Expand difficult concepts instead of summarizing them."""

    def _generate_partial(self, prompt, max_tokens=4096, retries=2, key=None, base_url=None, chat_model=None, custom_instr=""):
        """Call the LLM API with retry logic and robust JSON extraction."""
        if not key:
            key, base_url, chat_model, vision_model = self._get_config()
            custom_instr = self._get_custom_instructions()
            
        if not key:
            return {}
        
        # Detect if this is a local/custom model
        is_local = "127.0.0.1" in (base_url or "") or "localhost" in (base_url or "")
        
        if is_local:
            # Simplified system prompt for small local models — NO LaTeX
            system_prompt = self.HELIX_SYSTEM_PROMPT + """\n
CRITICAL JSON OUTPUT RULES:
1. Output ONLY valid JSON. No markdown wrappers, no extra text.
2. Do NOT use LaTeX, math notation, dollar signs ($), or backslash commands.
3. Write math in plain text: "x^2 + y^2 = z^2" not "$x^2$".
4. Write fractions as "a/b" not "\\frac{a}{b}".
5. Every string must be properly closed with a quote.
6. Do not nest JSON inside JSON strings.
7. Keep answers concise to avoid truncation."""
        else:
            system_prompt = self.HELIX_SYSTEM_PROMPT + """\n
CRITICAL JSON OUTPUT RULES:
1. Output ONLY valid JSON. No markdown wrappers, no extra text.
2. When writing math, use LaTeX: '$$...$$' for block equations, '$...$' for inline.
3. For programming code, use Markdown code blocks (```language), NEVER LaTeX.
4. Because you are outputting JSON, double-escape all LaTeX backslashes (e.g. \\\\frac instead of \\frac)."""
        
        if custom_instr:
            system_prompt += f"\n\nUSER'S CUSTOM INSTRUCTIONS FOR AI BEHAVIOR:\n{custom_instr}\n"

        payload = {
            "model": chat_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3 if is_local else 0.5,
            "top_p": 1,
            "max_tokens": max_tokens,
        }
        # Only use response_format for cloud APIs that support it reliably
        if not is_local:
            payload["response_format"] = {"type": "json_object"}
            
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        
        for attempt in range(retries + 1):
            try:
                response = requests.post(
                    f"{base_url}/chat/completions", 
                    headers=headers, 
                    json=payload,
                    timeout=600
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                result = self._extract_json(content)
                if result:
                    return result
                print(f"Empty JSON extraction on attempt {attempt + 1}")
            except requests.exceptions.HTTPError as e:
                _handle_auth_error(e)
                print(f"HTTP Error in partial generation attempt {attempt + 1}: {e}")
                if e.response and e.response.status_code == 429:
                    time.sleep(2 ** attempt)
                    continue
                if e.response and e.response.status_code >= 500:
                    time.sleep(1 * (attempt + 1))
                    continue
            except requests.exceptions.Timeout:
                print(f"Timeout on attempt {attempt + 1}")
                time.sleep(1)
            except Exception as e:
                print(f"Error in partial generation attempt {attempt + 1}: {e}")
                time.sleep(0.5)
        return {}

    def generate_study_materials(self, topic_name, subject_name="", key=None, base_url=None, chat_model=None, custom_instr=""):
        """
        Generates comprehensive notes, flashcards, MCQs, and Viva questions for a given topic IN PARALLEL.
        """
        # Fetch config and instructions in the main thread (with Flask request context) if not passed
        if not key:
            key, base_url, chat_model, _ = self._get_config()
            custom_instr = self._get_custom_instructions()
            
        if not key:
            return self._get_mock_materials_response(topic_name, subject_name)

        import concurrent.futures
        
        context_str = f" in the context of the subject '{subject_name}'" if subject_name else ""

        is_local_cpu = "127.0.0.1" in base_url or "localhost" in base_url

        if is_local_cpu:
            # Simplified prompts for small local models (Qwen 1.5 4B etc.)
            # NO LaTeX, NO complex formatting, SHORT outputs
            prompts = {
                "notes_summary": f"""Generate study notes for: '{topic_name}'{context_str}.
Cover: definition, key concepts, important points, examples, and a summary.
Write about 300 words of notes.
Write math in plain text like "x^2 + y^2" not LaTeX.
Also write a short 100-word revision summary.
Return JSON: {{"notes": "your notes here as a single string with markdown headings", "summary": "short summary here"}}""",
                "flashcards": f"""Generate 4 flashcards for: '{topic_name}'.
Each has a question and answer. Keep answers short (1-2 sentences).
No LaTeX or math symbols. Write math in plain text.
Return JSON: {{"flashcards": [{{"question": "...", "answer": "..."}}]}}""",
                "quizzes": f"""Generate 3 multiple choice questions for: '{topic_name}'.
Each has 4 options labeled A through D. No LaTeX or backslash commands.
Return JSON: {{"quizzes": [{{"question": "...", "options": ["A. ...", "B. ...", "C. ...", "D. ..."], "correct_index": 0, "explanation": "..."}}]}}""",
                "viva": f"""Generate 4 short-answer questions for: '{topic_name}'.
Keep answers to 1-2 sentences. No LaTeX or backslash commands.
Return JSON: {{"viva_questions": [{{"question": "...", "answer": "..."}}]}}"""
            }
        else:
            prompts = {
                "notes_summary": f"""
            Generate extremely detailed, comprehensive academic study notes for the topic: '{topic_name}'{context_str}.
            
            IMPORTANT: The notes MUST be at least 800 words. Be thorough and cover:
            - Definition and introduction to the concept
            - Core principles with detailed explanations (not just bullet points)
            - Key terminology with definitions
            - Step-by-step processes or algorithms if applicable
            - Real-world examples and practical applications
            - Common misconceptions and pitfalls
            - Comparison with related concepts
            - Advantages and disadvantages
            - Important formulas, theorems, proofs, or rules
            - Exam-oriented tips and key points to remember
            - **Step-by-step solved practice problems** with mathematical signs, derivations, and solutions
            
            STRICT ACADEMIC RULE: Do NOT include any historical backgrounds, conversational filler, or unnecessary fluff. A student needs to study efficiently. Focus purely on technical and academic facts, concepts, and problem-solving.
            
            MATH/EQUATIONS CONSTRAINT: You MUST convert ALL mathematical content to valid MathJax (LaTeX).
            This includes: Arithmetic, Algebra, Calculus, Matrices, Logic, Graph Theory, etc.
            Rules:
            - Convert every mathematical expression, symbol, formula, derivation, proof, piecewise function, or equation into valid LaTeX.
            - Use '$$...$$' for display equations and '$...$' for inline math.
            - Convert fractions to \\frac, roots to \\sqrt.
            - Use proper LaTeX commands for integrals, sums, limits, vectors, matrices, Greek letters, and all mathematical symbols.
            - Preserve all explanations, headings, lists, tables, and formatting.
            - Ensure the final output renders without errors in MathJax v3.
            
            CRITICAL JSON RULE: Because you are outputting JSON, you MUST double-escape all LaTeX backslashes so the JSON is valid. For example, write \\\\frac instead of \\frac.
            
            Also generate a separate concise revision summary (200-300 words).
            
            Return a strict JSON object:
            {{"notes": "<long markdown notes with headers, sub-headers, bullet points, code blocks, LaTeX equations>", "summary": "<concise revision summary>"}}
            """,
                "flashcards": f"""
            Generate exactly 10 high-quality flashcard objects for the topic: '{topic_name}'.
            Each flashcard should test a different key concept. 
            MATH CONSTRAINT: If the topic contains math/logic, use standard LaTeX math notation ('$$...$$' or '$...$') in questions/answers.
            CRITICAL JSON RULE: You MUST double-escape all LaTeX backslashes (e.g. \\\\frac instead of \\frac) for valid JSON.
            Return strict JSON:
            {{"flashcards": [{{"question": "...", "answer": "..."}}]}}
            """,
                "quizzes": f"""
            Generate exactly 5 MCQ quiz questions for the topic: '{topic_name}'.
            Each question should test understanding, not just recall.
            MATH CONSTRAINT: If the topic contains math/logic, use standard LaTeX math notation for equations and show step-by-step derivations in the explanation.
            CRITICAL JSON RULE: You MUST double-escape all LaTeX backslashes (e.g. \\\\frac instead of \\frac) for valid JSON.
            Return strict JSON:
            {{"quizzes": [{{"question": "...", "options": ["A", "B", "C", "D"], "correct_index": 0, "explanation": "..."}}]}}
            """,
                "viva": f"""
            Generate exactly 10 short-answer viva/oral exam questions with answers for: '{topic_name}'.
            MATH CONSTRAINT: If the topic contains math/logic, use standard LaTeX math notation.
            CRITICAL JSON RULE: You MUST double-escape all LaTeX backslashes for valid JSON.
            Return strict JSON:
            {{"viva_questions": [{{"question": "...", "answer": "..."}}]}}
            """
            }

        results = {}
        # Use 1 worker for local CPU to prevent parallel request thrashing
        max_workers = 1 if is_local_cpu else 3
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_key = {}
            for pkey, prompt in prompts.items():
                if is_local_cpu:
                    # Low token limits for local CPU to generate fast
                    tokens = 1200 if pkey == "notes_summary" else 400
                else:
                    # Higher token limits for cloud APIs
                    tokens = 3072 if pkey == "notes_summary" else 1536
                future_to_key[executor.submit(self._generate_partial, prompt, tokens, 2, key, base_url, chat_model, custom_instr)] = pkey
            for future in concurrent.futures.as_completed(future_to_key):
                try:
                    data = future.result()
                    if data:
                        results.update(data)
                except Exception as e:
                    print(f"Parallel execution error: {e}")

        # If generation failed completely, return what we have (may be empty)
        # The task worker will detect empty notes and mark the task as failed
        if not results.get("notes") and not results.get("summary"):
            print(f"AI generation failed completely for topic: {topic_name}")
            return {
                "notes": "",
                "summary": "",
                "flashcards": results.get("flashcards", []),
                "quizzes": results.get("quizzes", []),
                "viva_questions": results.get("viva_questions", []),
                "_generation_failed": True
            }
            
        final_result = {
            "notes": results.get("notes", ""),
            "summary": results.get("summary", ""),
            "flashcards": results.get("flashcards", []),
            "quizzes": results.get("quizzes", []),
            "viva_questions": results.get("viva_questions", [])
        }
        return final_result

    def _get_mock_vision_response(self):
        return {
            "title": "Sample Study Notes",
            "subject": "Computer Science",
            "unit": "Unit 1: Introductions",
            "topics": ["Artificial Intelligence", "Machine Learning", "Deep Learning"],
            "summary": "This document outlines the foundational definitions of AI, ML, and DL, showing their hierarchical relationship.",
            "full_text": "Artificial Intelligence is the broad concept of machines being able to carry out tasks in a smart way. Machine Learning is an application of AI based around the idea that we should give machines access to data and let them learn for themselves. Deep Learning is a subset of ML inspired by the structure of the human brain (neural networks).",
            "important_points": [
                "AI is the parent field.",
                "ML relies on data learning.",
                "DL uses deep artificial neural networks."
            ],
            "questions": [
                "Explain the key difference between Machine Learning and Deep Learning.",
                "What is the inspiration behind Deep Learning models?"
            ],
            "keywords": ["AI", "Machine Learning", "Neural Networks", "Deep Learning"]
        }

    def _get_mock_syllabus_response(self):
        return {
            "subjects": [
                {
                    "name": "Database Management Systems",
                    "code": "CS-302",
                    "units": [
                        {
                            "name": "Introduction & ER Model",
                            "number": 1,
                            "topics": ["DBMS Architecture", "Entity Relationship Diagrams", "Relational Model Concepts"]
                        },
                        {
                            "name": "Structured Query Language (SQL)",
                            "number": 2,
                            "topics": ["DDL & DML Queries", "Joins and Subqueries", "Triggers and Views"]
                        }
                    ]
                }
            ]
        }

    def _get_mock_materials_response(self, topic_name=None, subject_name=""):
        if topic_name:
            topic_lower = topic_name.lower().strip()
            subject_lower = subject_name.lower().strip()
            combined_context = f"{topic_lower} {subject_lower}"
            
            # ── Detect domain ──
            is_math = any(k in combined_context for k in [
                "math", "calculus", "algebra", "differentiat", "integrat", "derivative",
                "equation", "formula", "theorem", "proof", "trigonometr", "logarithm",
                "limit", "matrix", "matrices", "polynomial", "quadratic", "linear",
                "probability", "statistics", "number theory", "discrete", "graph theory",
                "geometry", "vector", "differential", "series", "sequence", "function"
            ])
            is_physics = any(k in combined_context for k in [
                "physics", "mechanics", "thermodynamic", "electr", "magnet", "optic",
                "wave", "quantum", "relativity", "newton", "force", "motion", "energy",
                "momentum", "gravit", "circuit", "resistor", "capacitor"
            ])
            is_chemistry = any(k in combined_context for k in [
                "chemistry", "chemical", "reaction", "organic", "inorganic", "periodic",
                "bond", "molecule", "atom", "compound", "acid", "base", "oxidation",
                "reduction", "electrochemistry", "thermochemistry"
            ])
            is_biology = any(k in combined_context for k in [
                "biology", "cell", "dna", "rna", "genetics", "evolution", "ecology",
                "anatomy", "physiology", "microb", "botan", "zoolog"
            ])
            
            # ── Domain-specific content ──
            if is_math:
                # Differentiation-specific check
                if any(k in combined_context for k in ["differentiat", "derivative"]):
                    notes_text = f"""# {topic_name}

## 1. Introduction

**{topic_name}** are the fundamental rules used in calculus to find the derivative of a function. The derivative measures the rate at which a function's output changes with respect to its input.

## 2. Key Differentiation Rules

### 2.1 Constant Rule
If f(x) = c (a constant), then f'(x) = 0.

### 2.2 Power Rule
If f(x) = x^n, then f'(x) = n * x^(n-1).
- Example: f(x) = x^3, then f'(x) = 3x^2

### 2.3 Constant Multiple Rule
If f(x) = c * g(x), then f'(x) = c * g'(x).

### 2.4 Sum/Difference Rule
If f(x) = g(x) +/- h(x), then f'(x) = g'(x) +/- h'(x).

### 2.5 Product Rule
If f(x) = g(x) * h(x), then f'(x) = g'(x)*h(x) + g(x)*h'(x).

### 2.6 Quotient Rule
If f(x) = g(x)/h(x), then f'(x) = [g'(x)*h(x) - g(x)*h'(x)] / [h(x)]^2.

### 2.7 Chain Rule
If f(x) = g(h(x)), then f'(x) = g'(h(x)) * h'(x).

## 3. Common Derivatives Table

| Function f(x) | Derivative f'(x) |
|---|---|
| x^n | n * x^(n-1) |
| e^x | e^x |
| ln(x) | 1/x |
| sin(x) | cos(x) |
| cos(x) | -sin(x) |
| tan(x) | sec^2(x) |

## 4. Solved Examples

**Example 1:** Find the derivative of f(x) = 3x^4 - 5x^2 + 7x - 2
- f'(x) = 12x^3 - 10x + 7

**Example 2:** Find the derivative of f(x) = (2x + 1)^5
Using Chain Rule: f'(x) = 5(2x + 1)^4 * 2 = 10(2x + 1)^4

**Example 3:** Find the derivative of f(x) = x^2 * sin(x)
Using Product Rule: f'(x) = 2x * sin(x) + x^2 * cos(x)

## 5. Common Mistakes
1. Forgetting to apply the chain rule to composite functions
2. Confusing the product rule with simply multiplying derivatives
3. Sign errors in the quotient rule
4. Forgetting that the derivative of a constant is 0

## 6. Exam Tips
- Memorize the standard derivatives table
- Always identify if the function is a product, quotient, or composition before differentiating
- Practice chain rule problems extensively
- Show all intermediate steps in exam answers"""
                    summary_text = f"{topic_name} include: Constant Rule (d/dx[c]=0), Power Rule (d/dx[x^n]=nx^(n-1)), Sum/Difference Rule, Product Rule (fg' + gf'), Quotient Rule, and Chain Rule (d/dx[f(g(x))] = f'(g(x))*g'(x)). Standard derivatives to memorize: d/dx[e^x]=e^x, d/dx[sin(x)]=cos(x), d/dx[ln(x)]=1/x."
                elif any(k in combined_context for k in ["integrat"]):
                    notes_text = f"""# {topic_name}

## 1. Introduction
**{topic_name}** is the reverse process of differentiation. Integration finds the antiderivative or area under a curve.

## 2. Basic Integration Rules

### 2.1 Power Rule for Integration
Integral of x^n dx = x^(n+1)/(n+1) + C, where n != -1

### 2.2 Constant Multiple Rule
Integral of c*f(x) dx = c * Integral of f(x) dx

### 2.3 Sum/Difference Rule
Integral of [f(x) +/- g(x)] dx = Integral of f(x) dx +/- Integral of g(x) dx

## 3. Standard Integrals

| Function | Integral |
|---|---|
| x^n | x^(n+1)/(n+1) + C |
| 1/x | ln|x| + C |
| e^x | e^x + C |
| sin(x) | -cos(x) + C |
| cos(x) | sin(x) + C |
| sec^2(x) | tan(x) + C |

## 4. Techniques of Integration
- **Substitution Method** (u-substitution)
- **Integration by Parts**: Integral of u dv = uv - Integral of v du
- **Partial Fractions**: For rational functions
- **Trigonometric Substitution**: For expressions involving sqrt(a^2 - x^2) etc.

## 5. Definite vs Indefinite Integrals
- **Indefinite integral**: Has + C (constant of integration)
- **Definite integral**: Has upper and lower limits, gives a numerical value

## 6. Solved Examples
**Example 1:** Integral of (3x^2 + 2x - 5) dx = x^3 + x^2 - 5x + C
**Example 2:** Integral of sin(3x) dx = -cos(3x)/3 + C (using substitution)"""
                    summary_text = f"{topic_name} covers antiderivatives and area computation. Key rules: Power Rule (x^(n+1)/(n+1)), standard integrals of trigonometric/exponential functions, and techniques like substitution, integration by parts, and partial fractions."
                else:
                    notes_text = f"""# {topic_name}

## 1. Introduction
**{topic_name}** is a fundamental concept in mathematics. This topic provides essential tools for problem-solving in algebra, calculus, and applied mathematics.

## 2. Core Concepts
- Definition and formal notation
- Key properties and theorems
- Relationship with other mathematical concepts
- Standard formulas and identities

## 3. Important Formulas
The key formulas and identities related to {topic_name} should be memorized for exams and practical applications.

## 4. Solved Examples
Step-by-step worked examples demonstrating the application of {topic_name} concepts.

## 5. Common Mistakes
1. Algebraic sign errors
2. Incorrect formula application
3. Missing edge cases or special conditions
4. Not simplifying final answers

## 6. Practice Problems
Regular practice with increasing difficulty levels is essential for mastery of {topic_name}."""
                    summary_text = f"{topic_name} is a core mathematical concept covering definitions, formulas, theorems, and problem-solving techniques. Essential for exams and practical applications in science and engineering."

                # Math flashcards
                if any(k in combined_context for k in ["differentiat", "derivative"]):
                    flashcards = [
                        {"question": "What is the Power Rule of differentiation?", "answer": "If f(x) = x^n, then f'(x) = n * x^(n-1). For example, d/dx[x^5] = 5x^4."},
                        {"question": "State the Product Rule.", "answer": "If f(x) = g(x)*h(x), then f'(x) = g'(x)*h(x) + g(x)*h'(x)."},
                        {"question": "What is the Chain Rule?", "answer": "If f(x) = g(h(x)), then f'(x) = g'(h(x)) * h'(x). Used for composite functions."},
                        {"question": "What is the derivative of sin(x)?", "answer": "The derivative of sin(x) is cos(x)."},
                        {"question": "State the Quotient Rule.", "answer": "If f(x) = g(x)/h(x), then f'(x) = [g'(x)*h(x) - g(x)*h'(x)] / [h(x)]^2."},
                    ]
                    quizzes = [
                        {"question": "What is the derivative of f(x) = 3x^4?", "options": ["12x^3", "12x^4", "3x^3", "4x^3"], "correct_index": 0, "explanation": "Using the Power Rule: f'(x) = 3 * 4 * x^(4-1) = 12x^3."},
                        {"question": "What is d/dx[e^x]?", "options": ["e^x", "x*e^(x-1)", "e^(x-1)", "1/e^x"], "correct_index": 0, "explanation": "The derivative of e^x is always e^x. This is a fundamental result."},
                        {"question": "Which rule is used to differentiate f(x) = sin(x^2)?", "options": ["Chain Rule", "Product Rule", "Power Rule", "Quotient Rule"], "correct_index": 0, "explanation": "sin(x^2) is a composite function: outer=sin, inner=x^2. Chain rule gives: cos(x^2) * 2x."},
                        {"question": "What is d/dx[ln(x)]?", "options": ["1/x", "ln(x)/x", "x", "e^x"], "correct_index": 0, "explanation": "The derivative of the natural logarithm ln(x) is 1/x."},
                    ]
                    viva = [
                        {"question": "Define differentiation.", "answer": "Differentiation is the process of finding the derivative of a function, measuring its instantaneous rate of change."},
                        {"question": "State the Power Rule.", "answer": "If f(x) = x^n, then f'(x) = n*x^(n-1)."},
                        {"question": "When do you use the Chain Rule?", "answer": "The Chain Rule is used when differentiating composite functions, i.e., a function inside another function."},
                        {"question": "What is the derivative of a constant?", "answer": "The derivative of any constant is 0."},
                        {"question": "How does the Product Rule differ from simply multiplying derivatives?", "answer": "The Product Rule states d/dx[f*g] = f'g + fg', NOT f'*g'. You cannot just multiply the individual derivatives."},
                    ]
                else:
                    flashcards = [
                        {"question": f"What is {topic_name}?", "answer": f"{topic_name} is a mathematical concept involving specific formulas, rules, and problem-solving techniques used in academic and applied contexts."},
                        {"question": f"Why is {topic_name} important?", "answer": f"It provides foundational tools for solving complex problems in mathematics, engineering, and science."},
                        {"question": f"What are the key formulas in {topic_name}?", "answer": "The key formulas depend on the specific subtopic but generally involve algebraic identities, function properties, and transformation rules."},
                        {"question": f"Name a common mistake in {topic_name}.", "answer": "Common mistakes include sign errors, incorrect formula application, and not checking special cases or boundary conditions."},
                    ]
                    quizzes = [
                        {"question": f"Which field does {topic_name} belong to?", "options": ["Mathematics", "Literature", "Geography", "History"], "correct_index": 0, "explanation": f"{topic_name} is a mathematical concept."},
                        {"question": f"What is essential for mastering {topic_name}?", "options": ["Regular practice with problems", "Memorizing Wikipedia articles", "Watching movies", "Physical exercise"], "correct_index": 0, "explanation": "Mathematical topics require consistent practice."},
                    ]
                    viva = [
                        {"question": f"Define {topic_name} in your own words.", "answer": f"{topic_name} involves mathematical principles, formulas, and techniques for solving specific types of problems."},
                        {"question": f"Give one practical application of {topic_name}.", "answer": f"{topic_name} is applied in engineering, physics, data science, and many real-world problem-solving scenarios."},
                    ]

            elif is_physics:
                notes_text = f"""# {topic_name}

## 1. Introduction
**{topic_name}** is a fundamental topic in Physics that describes how physical systems behave under specific conditions.

## 2. Core Principles
- Key laws and principles governing {topic_name}
- Mathematical formulations and equations
- Units of measurement and dimensional analysis

## 3. Important Formulas
The key equations and relationships for {topic_name} form the basis of problem-solving.

## 4. Applications
{topic_name} has applications in engineering, technology, and everyday life.

## 5. Solved Problems
Step-by-step solutions demonstrating the application of {topic_name} principles."""
                summary_text = f"{topic_name} is a Physics concept covering fundamental laws, equations, and practical applications. Key focus areas include mathematical formulations and real-world problem-solving."
                flashcards = [
                    {"question": f"What is {topic_name}?", "answer": f"{topic_name} describes physical phenomena governed by specific laws and mathematical equations."},
                    {"question": f"Name a key formula in {topic_name}.", "answer": f"The core formulas depend on the specific aspect of {topic_name} being studied."},
                ]
                quizzes = [{"question": f"Which branch of science does {topic_name} belong to?", "options": ["Physics", "Chemistry", "Biology", "Computer Science"], "correct_index": 0, "explanation": f"{topic_name} is a Physics topic."}]
                viva = [{"question": f"Explain the significance of {topic_name}.", "answer": f"{topic_name} helps us understand natural phenomena and build engineering solutions."}]

            elif is_chemistry:
                notes_text = f"""# {topic_name}

## 1. Introduction
**{topic_name}** is a core Chemistry concept covering the behavior of matter at the atomic and molecular level.

## 2. Key Concepts
- Atomic/molecular structure
- Reactions and mechanisms
- Thermodynamic and kinetic aspects
- Practical applications

## 3. Important Reactions and Equations
The balanced equations and reaction mechanisms related to {topic_name}.

## 4. Applications
Industrial, pharmaceutical, and environmental applications of {topic_name}."""
                summary_text = f"{topic_name} is a Chemistry concept covering reactions, molecular behavior, and practical applications in industry and research."
                flashcards = [
                    {"question": f"What is {topic_name}?", "answer": f"{topic_name} involves chemical principles, reactions, and molecular-level understanding of matter."},
                ]
                quizzes = [{"question": f"Which subject does {topic_name} belong to?", "options": ["Chemistry", "Mathematics", "History", "Geography"], "correct_index": 0, "explanation": f"{topic_name} is a Chemistry concept."}]
                viva = [{"question": f"Explain {topic_name} briefly.", "answer": f"{topic_name} covers chemical principles and their applications."}]

            else:
                # Generic academic fallback (not CS-specific)
                notes_text = f"""# {topic_name}

## 1. Introduction and Definition
**{topic_name}** is an important academic concept. Understanding this topic thoroughly is essential for exams and practical applications.

## 2. Core Concepts and Principles
- Key definitions and terminology
- Fundamental principles and rules
- Important relationships and connections

## 3. Detailed Explanation
{topic_name} involves understanding several interconnected ideas:
1. **Foundation** — The basic building blocks of the concept
2. **Application** — How the concept is applied in practice
3. **Analysis** — Breaking down complex scenarios
4. **Evaluation** — Assessing results and drawing conclusions

## 4. Practical Examples
Understanding {topic_name} requires working through real examples and practice problems.

## 5. Common Mistakes
1. Misunderstanding key definitions
2. Incorrect application of rules
3. Not considering edge cases
4. Rushing through problems without checking work

## 6. Exam Tips
- Understand the 'why' behind each concept, not just the 'what'
- Practice with past exam papers
- Create summary sheets for quick revision
- Focus on commonly tested subtopics"""
                summary_text = f"{topic_name} covers key definitions, principles, practical applications, and problem-solving techniques. Regular practice and understanding of core concepts is essential for mastery."
                flashcards = [
                    {"question": f"What is {topic_name}?", "answer": f"{topic_name} is an academic concept involving specific principles, rules, and practical applications within its field."},
                    {"question": f"Why is {topic_name} important?", "answer": f"Understanding {topic_name} is essential for exams and provides the foundation for advanced topics in the field."},
                    {"question": f"What are common mistakes in {topic_name}?", "answer": "Common mistakes include misunderstanding definitions, incorrect rule application, and not considering special cases."},
                ]
                quizzes = [
                    {"question": f"Which approach is best for studying {topic_name}?", "options": ["Understanding concepts and practicing problems", "Only reading notes once", "Skipping difficult sections", "Memorizing without understanding"], "correct_index": 0, "explanation": "Active learning through practice and understanding is the most effective approach."},
                ]
                viva = [
                    {"question": f"Define {topic_name} in your own words.", "answer": f"{topic_name} involves understanding specific principles and their applications within the broader subject area."},
                    {"question": f"Give a practical application of {topic_name}.", "answer": f"{topic_name} can be applied in real-world scenarios related to its field of study."},
                ]

            return {
                "notes": notes_text,
                "summary": summary_text,
                "flashcards": flashcards,
                "quizzes": quizzes,
                "viva_questions": viva,
            }

    SUBJECT_DATA = {
        "dbms": {
            "name": "Database Management Systems",
            "code": "CS-302",
            "aliases": ["dbms", "database", "sql"],
            "units": [
                {"name": "Intro & ER Model", "number": 1, "topics": ["Introduction to DBMS", "ER Model"]},
                {"name": "Relational Model", "number": 2, "topics": ["Relational Algebra", "Tuple Calculus"]},
                {"name": "SQL", "number": 3, "topics": ["DDL and DML", "Joins and Subqueries"]},
                {"name": "Normalization", "number": 4, "topics": ["1NF to 3NF", "BCNF"]},
                {"name": "Transactions & Concurrency", "number": 5, "topics": ["ACID Properties", "Concurrency Control"]}
            ]
        },
        "computer networks": {
            "name": "Computer Networks",
            "code": "CS-303",
            "aliases": ["computer networks", "networking", "cn"],
            "units": [
                {"name": "Network Models", "number": 1, "topics": ["OSI Model", "TCP/IP Suite"]},
                {"name": "Data Link Layer", "number": 2, "topics": ["Error Detection", "MAC Protocols"]},
                {"name": "Network Layer", "number": 3, "topics": ["IPv4 and IPv6", "Routing Algorithms"]},
                {"name": "Transport Layer", "number": 4, "topics": ["TCP", "UDP"]},
                {"name": "Application Layer", "number": 5, "topics": ["HTTP", "DNS"]}
            ]
        },
        "operating systems": {
            "name": "Operating Systems",
            "code": "CS-304",
            "aliases": ["operating systems", "os", "linux"],
            "units": [
                {"name": "Process Management", "number": 1, "topics": ["Processes and Threads", "Process Synchronization"]},
                {"name": "CPU Scheduling", "number": 2, "topics": ["Scheduling Algorithms"]},
                {"name": "Memory Management", "number": 3, "topics": ["Paging and Segmentation", "Virtual Memory"]},
                {"name": "File Systems", "number": 4, "topics": ["File Access Methods", "Directory Structure"]},
                {"name": "Deadlocks", "number": 5, "topics": ["Deadlock Prevention", "Deadlock Avoidance"]}
            ]
        },
        "data structures": {
            "name": "Data Structures",
            "code": "CS-201",
            "aliases": ["data structures", "dsa", "algorithms"],
            "units": [
                {"name": "Arrays & Linked Lists", "number": 1, "topics": ["Arrays", "Singly Linked List"]},
                {"name": "Stacks & Queues", "number": 2, "topics": ["Stack Operations", "Queue Types"]},
                {"name": "Trees", "number": 3, "topics": ["Binary Trees", "BST"]},
                {"name": "Graphs", "number": 4, "topics": ["Graph Traversals", "Shortest Path"]},
                {"name": "Sorting & Searching", "number": 5, "topics": ["Quick Sort", "Binary Search"]}
            ]
        },
        "software engineering": {
            "name": "Software Engineering",
            "code": "CS-401",
            "aliases": ["software engineering", "se", "sdlc"],
            "units": [
                {"name": "SDLC Models", "number": 1, "topics": ["Waterfall Model", "Agile Methodology"]},
                {"name": "Requirements Engineering", "number": 2, "topics": ["Requirements Elicitation", "SRS Document"]},
                {"name": "Design Patterns", "number": 3, "topics": ["Creational Patterns", "Structural Patterns"]},
                {"name": "Testing", "number": 4, "topics": ["Unit Testing", "Integration Testing"]},
                {"name": "Project Management", "number": 5, "topics": ["Risk Management", "Cost Estimation"]}
            ]
        }
    }

    def _detect_subject(self, command_lower):
        """Detect subject from command text using alias matching."""
        for key, data in self.SUBJECT_DATA.items():
            for alias in data["aliases"]:
                if alias in command_lower:
                    return key, data
        return None, None

    def _detect_semester(self, command_lower):
        """Extract semester info from command text."""
        import re
        # Match patterns like '5th semester', 'semester 3', 'sem 4', '3rd sem'
        patterns = [
            r'(\d+)(?:st|nd|rd|th)?\s*(?:semester|sem)',
            r'(?:semester|sem)\s*(\d+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, command_lower)
            if match:
                return int(match.group(1))
        return None

    def _detect_focus_topics(self, command_lower, subject_data):
        """Extract focus topics mentioned in the command."""
        focus = []
        if subject_data:
            all_topics = []
            for unit in subject_data["units"]:
                all_topics.extend(unit["topics"])
            for topic in all_topics:
                if topic.lower() in command_lower:
                    focus.append(topic)
            # Also check for unit-name-level keywords
            for unit in subject_data["units"]:
                unit_name_lower = unit["name"].lower()
                # Check individual words from unit name (skip short words)
                for word in unit_name_lower.split():
                    if len(word) > 3 and word in command_lower and word not in [w.lower() for w in focus]:
                        # Find the first topic in that unit as focus
                        focus.append(unit["name"])
                        break
        return list(set(focus)) if focus else []

    def process_natural_language_command(self, user_command):
        """
        Parse a natural language command into a structured action plan.
        Uses NVIDIA NIM when API key is set, otherwise falls back to
        intelligent keyword-based mock parsing.
        """
        if self.api_key:
            return self._nlp_command_via_nim(user_command)
        return self._nlp_command_mock(user_command)

    def _nlp_command_via_nim(self, user_command):
        """Send the command to NVIDIA NIM for structured parsing."""
        key, base_url, chat_model, vision_model = self._get_config()
        
        prompt = f"""
        You are a study planner AI. Parse the following natural language command into a structured JSON action plan.

        User command: "{user_command}"

        Return strict JSON in this exact format:
        {{
          "action": "create_study_structure",
          "semester": {{"name": "Semester X"}},
          "subjects": [
            {{
              "name": "Full Subject Name",
              "code": "CS-XXX",
              "units": [
                {{
                  "name": "Unit Name",
                  "number": 1,
                  "topics": ["Topic1", "Topic2"]
                }}
              ]
            }}
          ],
          "generate_materials": true,
          "focus_topics": ["Topic if mentioned"]
        }}

        Rules:
        - The subject name MUST be the exact subject the user asks for (e.g., if they ask for "Python", the subject name must be "Python"). DO NOT generate a random subject.
        - Infer the full subject name from abbreviations ONLY IF an abbreviation is used (DBMS = Database Management Systems, CN = Computer Networks, OS = Operating Systems, DS = Data Structures, SE = Software Engineering).
        - Generate 5 logical units with 3-4 topics each if the user does not specify.
        - CRITICAL: Even if the user explicitly names a unit, you MUST automatically expand that unit into at least 4-5 detailed academic sub-topics. Never create a unit with only 1 topic.
        - If the user mentions specific topics, include them in focus_topics.
        - Always set generate_materials to true if the user mentions topics, notes, or materials.
        """

        payload = {
            "model": chat_model,
            "messages": [
                {"role": "system", "content": "You are a study planning AI that converts natural language into structured academic plans. You MUST output valid JSON."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "top_p": 1,
            "max_tokens": 1024,
            "response_format": {"type": "json_object"}
        }

        try:
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            response = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            content = content.replace("```json", "").replace("```", "").strip()
            return json.loads(content)
        except Exception as e:
            print(f"Error in NLP command NIM API: {e}")
            return self._nlp_command_mock(user_command)

    def _nlp_command_mock(self, user_command):
        """Intelligent keyword-based mock parser for natural language commands."""
        cmd = user_command.lower().strip()

        # Detect semester
        sem_number = self._detect_semester(cmd)
        semester_name = f"Semester {sem_number}" if sem_number else "Semester 1"

        # Detect subject
        subject_key, subject_data = self._detect_subject(cmd)

        if not subject_data:
            # Default to DBMS if no subject detected
            subject_key = "dbms"
            subject_data = self.SUBJECT_DATA["dbms"]

        # Detect focus topics
        focus_topics = self._detect_focus_topics(cmd, subject_data)

        # Determine if materials should be generated
        generate_materials = bool(focus_topics) or any(
            kw in cmd for kw in ["generate", "create", "material", "notes", "study", "learn"]
        )

        return {
            "action": "create_study_structure",
            "semester": {"name": semester_name},
            "subjects": [
                {
                    "name": subject_data["name"],
                    "code": subject_data["code"],
                    "units": [
                        {
                            "name": unit["name"],
                            "number": unit["number"],
                            "topics": list(unit["topics"]),
                        }
                        for unit in subject_data["units"]
                    ],
                }
            ],
            "generate_materials": generate_materials,
            "focus_topics": focus_topics,
        }

    def generate_topic_materials_for_name(self, topic_name, subject_name="", key=None, base_url=None, chat_model=None, custom_instr=""):
        """
        Generate enriched, topic-specific study materials.
        Uses NVIDIA NIM when available; otherwise returns curated mock data
        for known topics or delegates to the generic mock fallback.
        """
        actual_key = key or self.api_key
        if actual_key:
            return self.generate_study_materials(topic_name, subject_name, key=actual_key, base_url=base_url, chat_model=chat_model, custom_instr=custom_instr)

        # Fallback: generate a reasonable mock for unknown topics
        return {
            "notes": f"# {topic_name}\n\n## Overview\n{topic_name} is a fundamental concept in computer science that every student should master.\n\n## Key Concepts\n- Core principles and definitions\n- Practical applications and use cases\n- Common implementation patterns\n- Performance considerations\n\n## Summary\nUnderstanding {topic_name} is essential for building a strong foundation in this subject area.",
            "summary": f"{topic_name} covers fundamental principles, practical applications, and implementation strategies that are essential for academic and professional success.",
            "flashcards": [
                {"question": f"What is {topic_name}?", "answer": f"{topic_name} is a key concept that involves understanding core principles and their practical applications in the field."},
                {"question": f"Why is {topic_name} important?", "answer": f"{topic_name} provides foundational knowledge required for advanced topics and real-world problem solving."},
            ],
            "quizzes": [
                {
                    "question": f"Which of the following best describes {topic_name}?",
                    "options": [
                        f"A fundamental concept in the subject",
                        "An unrelated mathematical theorem",
                        "A hardware component",
                        "A programming language",
                    ],
                    "correct_index": 0,
                    "explanation": f"{topic_name} is a core concept within its subject domain.",
                }
            ],
            "viva_questions": [
                {"question": f"Explain the significance of {topic_name}.", "answer": f"{topic_name} is significant because it forms the basis for understanding more advanced concepts and has wide practical applications."},
            ],
        }

ai_service = AIService()
