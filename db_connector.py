import mysql.connector

def get_conn():
    return mysql.connector.connect(host='localhost', user='root', password='1234',database="credit_card_recommendation")


