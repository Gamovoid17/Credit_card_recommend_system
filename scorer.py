import mysql.connector

# scorer_module.py
from db_connector import get_conn   


# Scoring for credit cards  ----------
def get_category_match_score(reward_type, spend_categories):
    category_map = { "fuel": 0, "travel": 1, "groceries": 2, "dining": 3 }
    idx = category_map.get(reward_type.lower())
    if idx is None:
        return 0
    spend = spend_categories[idx]
    return min((spend / 10_000) * 15, 15)  

def score_card(user, card):
    
    # 1. Hard income gate
    try:
        min_income = int(''.join(filter(str.isdigit,
                card['eligibility_criteria'].split('₹')[-1].split('/')[0].replace(',', '').replace('L', '0000'))))
        if user['monthly_income'] < min_income:
            return 0
    except:
        return 0

    # 2. Hard credit‑score gate
    user_score = None
    if user['credit_score'].lower() != 'unknown':
        try:
            user_score = int(user['credit_score'])
            if user_score < card['min_credit_score']:
                return 0
        except:
            return 0


    # soft scoring --------
    score = 0
    if user['preferred_benefits'].lower() == card['perk'].lower():
        score += 30

    spend_vec = [user['spend_fuel'], user['spend_travel'],
                 user['spend_groceries'], user['spend_dining']]
    score += get_category_match_score(card['reward_type'], spend_vec)
    score += 15                                                 # income bonus
    if user_score:
        score += 15                                             # credit bonus
    if isinstance(card.get('reward_rate'), (int, float)):
        score += min((card['reward_rate'] / 20) * 15, 15)

    return round(score, 2)


# ---------- Main recommend section ----------
def recommend_top_cards(user_id, top_n=5):
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)

        cur.execute("SELECT * FROM user_profiles WHERE id=%s", (user_id,))
        user = cur.fetchone()
        if not user:
            print(f"No user id {user_id}")
            return []

        cur.execute("SELECT * FROM credit_cards")
        cards = cur.fetchall()

    scored = [dict(card, score=score_card(user, card))
              for card in cards if (scr := score_card(user, card)) > 0]

    scored.sort(key=lambda c: c['score'], reverse=True)
    return scored[:top_n]

# ---------- quick demo ----------
if __name__ == "__main__":
    with get_conn() as conn:
        cur = conn.cursor()

        sample = {
            'monthly_income': 55_000,
            'spend_fuel': 3000, 'spend_travel': 4000,
            'spend_groceries': 6000, 'spend_dining': 2500,
            'preferred_benefits': 'cashback', 'credit_score': '720'
        }
        cur.execute("""
            INSERT INTO user_profiles
              (monthly_income, spend_fuel, spend_travel, spend_groceries, spend_dining,
               preferred_benefits, credit_score)
            VALUES (%(monthly_income)s, %(spend_fuel)s, %(spend_travel)s,
                    %(spend_groceries)s, %(spend_dining)s,
                    %(preferred_benefits)s, %(credit_score)s)
        """, sample)
        conn.commit()
        new_id = cur.lastrowid
        print("Inserted sample user", new_id)

    best = recommend_top_cards(new_id)
    if best:
        print("\nTop cards:")
        for c in best:
            print(f"- {c['card_name']} | Score {c['score']} | Perk {c['perk']}")
    else:
        print("No suitable cards found.")


print("Hello world")
