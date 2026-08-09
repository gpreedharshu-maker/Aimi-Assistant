from flask import Flask, render_template, request
from google import genai
from groq import Groq
from tavily import TavilyClient
from dotenv import load_dotenv
import os

# ==========================================================
# LOAD ENVIRONMENT
# ==========================================================

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# ==========================================================
# FLASK
# ==========================================================

app = Flask(__name__)

# ==========================================================
# AI CLIENTS
# ==========================================================

gemini_client = None
groq_client = None
tavily_client = None

if GEMINI_API_KEY:
    gemini_client = genai.Client(
        api_key=GEMINI_API_KEY
    )

if GROQ_API_KEY:
    groq_client = Groq(
        api_key=GROQ_API_KEY
    )

if TAVILY_API_KEY:
    tavily_client = TavilyClient(
        api_key=TAVILY_API_KEY
    )

# ==========================================================
# AIMI INSTRUCTION
# ==========================================================

aimi_instruction = """
You are Aimi, a friendly, intelligent, helpful, and reliable AI assistant.

Your goal is to understand the user's request and provide the most useful
answer in a clear, simple, and organized way.

PERSONALITY:

- Friendly
- Helpful
- Calm
- Clear
- Encouraging
- Professional

IMPORTANT:

If CURRENT WEB INFORMATION is provided below, use it as the primary source
for current facts.

Do not contradict reliable current search information using old knowledge.

If the search information is insufficient, clearly say that the information
could not be verified.

GREETING RULE:

- Begin every response with a short friendly greeting.
- Use "Hello!", "Hi!", or "Hey there!"
- Keep the greeting short.

CLOSURE RULE:

- End every response with a short friendly closing.

ANSWER RULES:

1. Understand the user's question before answering.

2. Answer directly.

3. Use simple and easy-to-understand language.

4. Give accurate and relevant information.

5. Keep paragraphs short.

6. For multiple points, use numbered lists.

7. Every numbered point must be on a separate line.

8. Leave one blank line between numbered points.

9. Every bullet point must be on a separate line.

10. Use headings when useful.

11. Headings must be plain text.

12. Do NOT use bold, italic, hashtags, horizontal lines,
    Markdown tables, or Markdown code blocks.

13. Do not use unnecessary emojis.

14. If the user asks for steps, explain them in numbered order.

15. If the user asks for advantages, disadvantages, features,
    benefits, examples, or ideas, use numbered points.

16. If the user asks for a comparison, use a clear point-by-point structure.

17. If the user asks for code, provide clean and properly formatted code.

18. If the user asks for an explanation, explain it simply.

19. Never claim that you performed an action that you did not perform.

20. Never invent information.

21. If current web information is provided, prioritize it.

FINAL FORMAT CHECK:

- Numbered points must be on separate lines.
- Bullet points must be on separate lines.
- Headings must contain no Markdown symbols.
- Keep the answer clear and readable.
"""

# ==========================================================
# DETECT CURRENT INFORMATION QUESTIONS
# ==========================================================

def is_current_question(prompt):

    current_keywords = [
        "current",
        "currently",
        "latest",
        "today",
        "today's",
        "now",
        "right now",
        "recent",
        "recently",
        "this week",
        "this month",
        "this year",
        "who is the cm",
        "who is the chief minister",
        "who is the prime minister",
        "who is the president",
        "who is the governor",
        "latest news",
        "current news",
        "current price",
        "latest price",
        "recent update",
        "recent updates",
        "new update",
        "new updates",
        "what happened today",
        "who won",
        "latest result"
    ]

    question = prompt.lower().strip()

    return any(
        keyword in question
        for keyword in current_keywords
    )


# ==========================================================
# TAVILY SEARCH
# ==========================================================

def search_web(prompt):

    if not tavily_client:
        raise Exception("TAVILY_API_KEY is missing.")

    print("\nAIMI: Searching the web...")

    results = tavily_client.search(
        query=prompt,
        search_depth="advanced",
        max_results=5
    )

    web_information = []

    for result in results.get("results", []):

        title = result.get("title", "")
        content = result.get("content", "")
        url = result.get("url", "")

        web_information.append(
            f"TITLE: {title}\n"
            f"CONTENT: {content}\n"
            f"SOURCE: {url}\n"
        )

    if not web_information:
        raise Exception("No web search results found.")

    print("AIMI: Web search completed.")

    return "\n".join(web_information)


# ==========================================================
# GEMINI
# ==========================================================

def ask_gemini(prompt, web_information=None):

    if not gemini_client:
        raise Exception("GEMINI_API_KEY is missing.")

    final_prompt = aimi_instruction

    if web_information:

        final_prompt += """

CURRENT WEB INFORMATION:

Use the following search results to answer the user's question.

--------------------------------------------------

""" + web_information + """

--------------------------------------------------

Important:
- Prefer reliable and recent information.
- Do not invent information.
- If sources disagree, mention the uncertainty.
"""

    final_prompt += (
        "\n\nUSER PROMPT:\n"
        + prompt
    )

    response = gemini_client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=final_prompt
    )

    if not response.text:
        raise Exception("Gemini returned an empty response.")

    return response.text


# ==========================================================
# GROQ BACKUP
# ==========================================================

def ask_groq(prompt, web_information=None):

    if not groq_client:
        raise Exception("GROQ_API_KEY is missing.")

    system_prompt = aimi_instruction

    if web_information:

        system_prompt += """

CURRENT WEB INFORMATION:

Use the following information to answer the user's question.

--------------------------------------------------

""" + web_information + """

--------------------------------------------------

Use the current search information as the primary source.
Do not invent information.
"""

    response = groq_client.chat.completions.create(

        model="llama-3.3-70b-versatile",

        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    answer = response.choices[0].message.content

    if not answer:
        raise Exception("Groq returned an empty response.")

    return answer


# ==========================================================
# HOME
# ==========================================================

@app.route("/", methods=["GET", "POST"])
def home():

    answer = ""

    if request.method == "POST":

        prompt = request.form.get(
            "prompt",
            ""
        ).strip()

        if not prompt:

            answer = "Hello! Please enter a question."

            return render_template(
                "index.html",
                answer=answer
            )

        web_information = None

        # ==================================================
        # CURRENT QUESTION → TAVILY
        # ==================================================

        if is_current_question(prompt):

            try:

                web_information = search_web(prompt)

            except Exception as search_error:

                print("\n========== SEARCH ERROR ==========")
                print(type(search_error).__name__)
                print(str(search_error))
                print("==================================")

        # ==================================================
        # TRY GEMINI
        # ==================================================

        try:

            print("\nAIMI: Trying Gemini...")

            answer = ask_gemini(
                prompt,
                web_information
            )

            print("AIMI: Gemini response received.")

        # ==================================================
        # GEMINI FAILED → GROQ
        # ==================================================

        except Exception as gemini_error:

            print("\n========== GEMINI ERROR ==========")
            print(type(gemini_error).__name__)
            print(str(gemini_error))
            print("==================================")

            print("\nAIMI: Gemini unavailable.")
            print("AIMI: Switching to Groq backup...")

            try:

                answer = ask_groq(
                    prompt,
                    web_information
                )

                print("AIMI: Groq response received.")

            except Exception as groq_error:

                print("\n=========== GROQ ERROR ===========")
                print(type(groq_error).__name__)
                print(str(groq_error))
                print("==================================")

                answer = (
                    "Hello! AIMI is temporarily unable "
                    "to process your request. Please try again."
                )

    return render_template(
        "index.html",
        answer=answer
    )


# ==========================================================
# RUN
# ==========================================================

if __name__ == "__main__":
    app.run(debug=True)