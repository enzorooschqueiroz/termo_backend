from flask import Flask, request, jsonify
from app.db import get_connection
from app.redis_client import r
from app.models import create_tables_sql
from datetime import datetime
from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    CORS(app)  # Habilita CORS para todas as rotas

    def setup_db():
        # Caso queira forçar criação local (opcional)
        pass

    setup_db()

    @app.route('/resultado', methods=['POST'])
    def registrar_resultado():
        data = request.json
        nome = data.get('nome')
        tentativas = data.get('tentativas')
        tempo = data.get('tempo')  # tempo em segundos

        if not all([nome, tentativas, tempo]):
            return jsonify({'erro': 'Dados incompletos'}), 400

        conn = get_connection()
        cur = conn.cursor()

        # 1. Verifica ou cria jogador
        cur.execute("SELECT id FROM jogador WHERE nome = %s", (nome,))
        jogador = cur.fetchone()
        if jogador:
            jogador_id = jogador[0]
        else:
            cur.execute("INSERT INTO jogador (nome) VALUES (%s) RETURNING id", (nome,))
            jogador_id = cur.fetchone()[0]

        # 2. Pega a última palavra do dia
        cur.execute("SELECT id FROM palavra_dia ORDER BY criada_em DESC LIMIT 1")
        palavra = cur.fetchone()
        if not palavra:
            conn.rollback()
            cur.close()
            conn.close()
            return jsonify({'erro': 'Nenhuma palavra definida'}), 400

        palavra_id = palavra[0]

        # 3. Insere resultado
        cur.execute("""
            INSERT INTO resultado (jogador_id, palavra_id, tentativas, tempo_seg)
            VALUES (%s, %s, %s, %s)
        """, (jogador_id, palavra_id, tentativas, tempo))

        conn.commit()
        cur.close()
        conn.close()

        r.delete("ranking_top10")  # limpa cache

        return jsonify({'mensagem': 'Resultado registrado com sucesso!'})

    @app.route('/palavra', methods=['POST'])
    def definir_palavra():
        data = request.json
        palavra = data.get('palavra')

        if not palavra:
            return jsonify({'erro': 'Palavra ausente'}), 400

        # Grava no Redis para facilitar
        r.set("palavra_atual", palavra.lower())

        # Salva no banco também
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO palavra_dia (palavra) VALUES (%s)", (palavra.lower(),))
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({'mensagem': 'Palavra definida com sucesso'})

    @app.route('/palavra', methods=['GET'])
    def get_palavra():
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT palavra FROM palavra_dia
            ORDER BY criada_em DESC
            LIMIT 1
        """)
        resultado = cur.fetchone()
        
        cur.close()
        conn.close()

        if resultado:
            return jsonify({'palavra': resultado[0]})
        else:
            return jsonify({'erro': 'Nenhuma palavra definida ainda.'}), 404

    @app.route('/ranking', methods=['GET'])
    def ranking():
        cache = r.get("ranking_top10")
        if cache:
            ranking_data = eval(cache.decode('utf-8'))
            return jsonify({'ranking': ranking_data})

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT j.nome, r.tentativas, r.tempo_seg
            FROM resultado r
            JOIN jogador j ON r.jogador_id = j.id
            ORDER BY r.tentativas ASC, r.tempo_seg ASC
            LIMIT 10
        """)
        resultados = cur.fetchall()
        cur.close()
        conn.close()

        ranking_data = [
            {"nome": nome, "tentativas": tentativas, "tempo": tempo}
            for nome, tentativas, tempo in resultados
        ]
        r.set("ranking_top10", str(ranking_data), ex=300)

        return jsonify({'ranking': ranking_data})

    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({'status': 'ok'}), 200

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5003, debug=True)
