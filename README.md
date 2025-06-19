# Credit_card_recommend_system
An AI-powered credit card advisor for Indian users, built with FastAPI, LangChain, and Ollama. It chats with users to understand their spending habits and recommends the best credit cards based on income, expenses, perks, and credit score 

# Project structure
The project is divided in the following scipts and folders

main.py : The FastAPI server that handles incoming chat messages, processes them using a local LLM (via LangChain), logs interactions, and returns personalized credit card recommendations.
scorer.py ; Contains logic for ranking and recommending credit cards based on user profile data using a scoring algorithm.
db_utils.py : Provides utility functions (e.g., get_conn()) to connect and interact with the backend MySQL database.
schema.sql : SQL script to create necessary tables such as user_profiles and chat_history in the MySQL database.
style.css : Basic styling for the frontend chat interface.
index.html : The main UI for the credit card advisor chatbot, allowing users to interact via chat in a browser.

#Database tables
user_profiles:Stores user-specific information required for card recommendations. (monthly_income, spend_fuel, spend_travel, spend_groceries, spend_dining,preferred_benefits (cashback, travel points, or lounge access),credit_score)
credit_cards:Contains metadata and attributes about available credit cards. (card_name, issuer, perk_type, eligibility_criteria, reward_rate, and annual_fee)
chat_history:Logs the full conversation history between the user and the assistant.(user_id, role (user or bot), message (the actual message content),Enables context-aware conversations and improves user experience)

#Project workflow
1. User Interaction via Chat Interface
The project begins with a user visiting the web-based chat interface, built using HTML, CSS, and JavaScript. Upon arrival, the user is greeted by the virtual advisor and prompted to ask questions or share details. The chatbot maintains a natural, conversational flow, asking users for necessary financial information such as monthly income, typical spending on fuel, travel, groceries, and dining, as well as their preferred credit card perk (cashback, travel points, or lounge access), and credit score if known. This process is intuitive and flexible, aiming to collect only the missing information.

2. LLM-Powered Dialogue Management
User input is passed to the backend FastAPI server, where it is processed by a local large language model (LLM) running through Ollama. The prompt is managed via LangChain, which handles the memory and chaining logic. The model responds contextually—only prompting for details not yet received. Once all six required inputs are collected, the model produces a special trigger message in the format CALL_RECOMMENDER({…}), containing all the user's responses.

3. Backend Processing & Data Extraction
The FastAPI backend detects the CALL_RECOMMENDER signal, extracts the structured user data using regex and JSON parsing, and stores it in the user_profiles table in the MySQL database. The insertion is followed by logging the entire conversation—including both user and assistant messages—into the chat_history table for future reference or analysis. If JSON parsing fails, a fallback using Python’s ast.literal_eval ensures the data is still correctly interpreted.

4. Card Recommendation Engine
With the user profile now stored, the backend invokes a custom function called recommend_top_cards() which compares the user's profile against the available credit card data in the credit_cards table. Each card is scored based on how well it matches the user's preferences and spending habits. The cards with the highest relevance scores are then selected and prepared to be sent back to the user as a recommendation.

# Prompt flow
Ollama) to behave like a smart and helpful credit card advisor for Indian users. The prompt's primary responsibility is to gather key user inputs conversationally and respond with a structured command once all necessary data is collected.

We define the conversational logic using LangChain’s PromptTemplate, which allows us to inject dynamic user input into a static instruction framework.This allows for a far more interactive and user-friendly experience on the front end Here's how the prompt is structured:

template = """
You are a credit‑card advisor for Indian users.
Ask any missing questions from: monthly income, spend on fuel / travel / groceries / dining,
preferred perk (cashback | travel points | lounge access), credit score (or 'unknown').
Keep the chat short.

User: {user_input}

When you have ALL 6 answers, respond EXACTLY with:
CALL_RECOMMENDER({{"income": ..., "fuel": ..., "travel": ..., "groceries": ..., "dining": ..., "perk": ..., "score": ...}})
"""


This template ensures that the LLM always acts within a controlled context. It prompts for missing data if the user hasn't provided all six fields and instructs the model to stop once all required inputs are available.

#Flow of Execution

1.User Initiates Chat
2.The user sends an input like "Hi, I'm looking for a good credit card." This input is passed into the PromptTemplate and processed by the LLMChain.
LLM Asks for Missing Info
3.LangChain’s ConversationBufferMemory helps preserve the sequence of user inputs and model responses across turns so that the LLM doesn't forget past information during the dialogue.(The responses are stored in the chat_history table in sql(a better method to store should be used))
4.Once the model has gathered all required details, it responds strictly with a CALL_RECOMMENDER({...}) statement. This triggers the function and prints out the top recommendaations from the database of credits cards(currently contains 20)

