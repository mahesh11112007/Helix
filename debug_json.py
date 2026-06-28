import json
import re

text = """{
  "quizzes": [
    {
      "question": "Find the derivative of the function $$f(x) = \\frac{1}{\\tan(x)}$$ using the quotient rule.",
      "options": [
        "A. $-\\frac{\\sin^2(x)}{\\cos^2(x)}$",
        "B. $\\frac{\\sin(x)}{\\cos^2(x)}$",
        "C. $\\frac{\\cos^2(x)}{\\sin^2(x)}$",
        "D. $\\frac{\\sin^2(x)}{\\cos^2(x)}$"
      ],
      "correct_index": 2,
      "explanation": "To find the derivative of $f(x) = \\frac{1}{\\tan(x)}$, we use the quotient rule."
    }
  ]
}"""

print("Original text length:", len(text))

# Apply same logic as ai_service
text_cleaned = re.sub(r'(?<!\\)\\f(?=[a-zA-Z])', r'\\\\f', text)
text_cleaned = re.sub(r'(?<!\\)\\r(?=[a-zA-Z])', r'\\\\r', text_cleaned)
text_cleaned = re.sub(r'(?<!\\)\\t(?=[a-zA-Z])', r'\\\\t', text_cleaned)
text_cleaned = re.sub(r'(?<!\\)\\b(?=[a-zA-Z])', r'\\\\b', text_cleaned)
text_cleaned = re.sub(r'(?<!\\)\\n(?=abla|u\b|eq|otin|rightarrow|exists)', r'\\\\n', text_cleaned)
text_cleaned = re.sub(r'(?<!\\)\\(?![\\"/bfnrtu])', r'\\\\', text_cleaned)

print("Cleaned text:", text_cleaned)

try:
    parsed = json.loads(text_cleaned)
    print("SUCCESS!")
except json.JSONDecodeError as e:
    print("FAILED:", e)
