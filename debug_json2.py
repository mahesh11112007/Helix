import json
import re

text = r"""{
  "quizzes": [
    {
      "question": "Find the derivative of the function f(x) = \frac{\sin(x)}{\cos(x)} using the quotient rule. What is the derivative of the function?",
      "options": ["A) \frac{\cos(x)}{\sin^2(x)}", "B) \frac{\sin^2(x) + \cos^2(x)}{\cos^2(x)}", "C) \frac{\cos(x)}{\sin^2(x)}", "D) \frac{\sin(x)}{\cos^2(x)}"],
      "correct_index": 0,
      "explanation": "To find the derivative of f(x) = \frac{\sin(x)}{\cos(x)}, we use the quotient rule:\[f'(x) = \frac{\cos(x)\cos(x) - \sin(x)(-\sin(x))}{\cos^2(x)}\]\[f'(x) = \frac{\cos^2(x) + \sin^2(x)}{\cos^2(x)}\]\[f'(x) = \frac{1}{\cos^2(x)}\]\[f'(x) = \sec^2(x)\]"
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
