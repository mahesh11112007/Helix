import json
from services.ai_service import ai_service

text = r'''{
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
}'''

try:
    print(ai_service._clean_and_parse_json(text))
except Exception as e:
    print("Error:", e)
