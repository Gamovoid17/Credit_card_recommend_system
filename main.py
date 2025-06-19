# main.py  ── fully updated
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

# ───── Request model ─────
class ChatIn(BaseModel):
    message: str
    uid: Optional[str]     = None   
    user_id: Optional[str] = None   

# ───── Helpers ─────
def log_message(uid: str, role: str, msg: str):
    conn = get_conn(); cur = conn.cursor()
    cur.execute(
        "INSERT INTO chat_history(user_id, role, message) VALUES (%s,%s,%s)",
        (uid, role, msg)
    )
    
    conn.commit(); 
    conn.close()

# ───── Chat endpoint ─────

@app.post("/chat")
def chat(req: ChatIn):
    # accept either uid or user_id from the JSON
    uid = req.uid or req.user_id or str(uuid.uuid4())                           #Uses the UID function to generate random UID if not provided

    # 2. Main LLM running part    ----------------------
    try:
        raw   = chain.invoke({"user_input": req.message})
        reply = raw.get("text", str(raw)).strip()
    except Exception as e:
        print("⚠️  LLM error:", e)
        reply = "Sorry, LLM error."

    #  3. check for CALL_RECOMMENDER trigger    -----------------
    
    if reply.startswith("CALL_RECOMMENDER"):                                     # When reply starts with the card recommendation func, print final result
        m = re.search(r"CALL_RECOMMENDER\((.*?)\)", reply, re.DOTALL)
        if m:
            try:
                raw_json = m.group(1).strip()
                # try normal JSON first, then try Python  (sometimes provides, JOSON and sometimes provides dictionary, that's why 2 methods)
                try:
                    data = json.loads(raw_json)
                except json.JSONDecodeError:
                    data = ast.literal_eval(raw_json)

                # insert user profile
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

                # recommend cards function from the scorer script
                cards = recommend_top_cards(new_id)
                card_lines = [
                    f"{i+1}. {c['card_name']} – Score {c['score']} ({c['perk']})"
                    for i, c in enumerate(cards)
                ]
                reply = "Based on your inputs, here are your best cards:\n" + "\n".join(card_lines)

            except Exception as e:
                print("Data processing error", e)
                reply = "Sorry, I couldn't process your data."
        else:
            reply = "Parsing error somewhere"


# snippet to let the AI use the function after all information is given by user

    if reply.startswith("CALL_RECOMMENDER"):
        display_reply = "Thanks! Based on your inputs, The best credit cards for you are.."
    else:
        display_reply = reply

    return JSONResponse({"reply": display_reply, "uid": uid})



print("serverIP - http://localhost:8000")

'''
uvicorn main:app --reload
http://localhost:8000/

'''
