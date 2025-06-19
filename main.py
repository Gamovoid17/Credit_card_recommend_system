from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from langchain_ollama import OllamaLLM
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from scorer import recommend_top_cards
from db_connector import get_conn
import json, re, uuid, ast

# ───── FastAPI setup ─────
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=FileResponse)
def home():
    return FileResponse("static/index.html")

@app.get("/new_session")
def new_session():
    return {"uid": str(uuid.uuid4())}

# ───── LangChain setup ─────
llm = OllamaLLM(model="mistral")
memory = ConversationBufferMemory(return_messages=True)

template = """
You are a helpful, friendly credit-card advisor for Indian users.

Your goal is to collect the following information from the user in a conversational tone:
- Monthly income
- Monthly fuel expenses
- Monthly travel expenses
- Monthly grocery expenses
- Monthly dining expenses
- Preferred benefit (cashback, travel points, or lounge access)
- Credit score (or say 'unknown')

Ask follow-up questions only for the details that are missing.
Be short, warm, and friendly in your responses.

Once all 7 details are collected, respond casually with something like:
"Thanks! Based on your answers, I’ll now look for the best credit cards for you."
Then, on a new line, output exactly:

CALL_RECOMMENDER({{"income": ..., "fuel": ..., "travel": ..., "groceries": ..., "dining": ..., "perk": ..., "score": ...}})

User: {user_input}
"""

prompt = PromptTemplate(input_variables=["user_input"], template=template)
chain  = LLMChain(llm=llm, prompt=prompt)

class ChatIn(BaseModel):
    message: str
    uid: Optional[str]     = None   
    user_id: Optional[str] = None   

def log_message(uid: str, role: str, msg: str):
    conn = get_conn(); cur = conn.cursor()
    cur.execute(
        "INSERT INTO chat_history(user_id, role, message) VALUES (%s,%s,%s)",
        (uid, role, msg)
    )
    conn.commit(); conn.close()

# ───── Chat endpoint ─────
@app.post("/chat")
def chat(req: ChatIn):
    uid = req.uid or req.user_id or str(uuid.uuid4())

    # 1. LLM Chain
    try:
        raw = chain.invoke({"user_input": req.message})
        reply = raw.get("text", str(raw)).strip()
    except Exception as e:
        print("⚠️  LLM error:", e)
        return JSONResponse({"reply": "Sorry, internal error.", "uid": uid})

    # 2. Parse CALL_RECOMMENDER trigger
    match = re.search(r"CALL_RECOMMENDER\((.*?)\)", reply, re.DOTALL)
    if match:
        try:
            raw_json = match.group(1).strip()

            # Handle both JSON and Python dict format
            try:
                data = json.loads(raw_json)
            except json.JSONDecodeError:
                data = ast.literal_eval(raw_json)

            # Store profile in DB
            conn = get_conn(); cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO user_profiles
                (monthly_income, spend_fuel, spend_travel, spend_groceries, spend_dining,
                 preferred_benefits, credit_score)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    data["income"], data["fuel"], data["travel"], data["groceries"],
                    data["dining"], data["perk"], data["score"]
                )
            )
            new_id = cur.lastrowid
            conn.commit(); conn.close()

            # Score and get card recommendations
            cards = recommend_top_cards(new_id)
            card_lines = [
                f"{i+1}. {c['card_name']} – Score {c['score']} ({c['perk']})"
                for i, c in enumerate(cards)
            ]
            reply = "Based on your inputs, here are your best credit card options:\n" + "\n".join(card_lines)

        except Exception as e:
            print(" Data not proccesed:", e)
            reply = "something wrong."

    # 3. Return response
    return JSONResponse({"reply": reply, "uid": uid})


print("serverIP - http://localhost:8000")

# Run with:
# uvicorn main:app --reload
