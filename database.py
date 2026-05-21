import psycopg2
import os

def conectar():

    DATABASE_URL = os.getenv("DATABASE_URL")

    return psycopg2.connect(
        DATABASE_URL,
        sslmode='require'
    )


def criar_tabelas():

    conn = conectar()
    cursor = conn.cursor()

    # USUÁRIOS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuario (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(100),
            email VARCHAR(100) UNIQUE,
            senha VARCHAR(100),
            tipo VARCHAR(20)
        )
    """)

    # TURMAS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS turma (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(100)
        )
    """)

    # RELAÇÃO TURMA E CATEQUISTA
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS turma_catequista (
            id SERIAL PRIMARY KEY,
            turma_id INTEGER REFERENCES turma(id),
            catequista_id INTEGER REFERENCES usuario(id)
        )
    """)

    # CRIANÇAS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS crianca (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(100),
            turma_id INTEGER REFERENCES turma(id)
        )
    """)

    # PRESENÇAS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS presenca (
            id SERIAL PRIMARY KEY,
            crianca_id INTEGER REFERENCES crianca(id),
            data DATE,
            status VARCHAR(20),
            justificativa TEXT
        )
    """)

    conn.commit()
    conn.close()