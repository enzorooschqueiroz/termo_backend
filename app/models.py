create_tables_sql = """
CREATE TABLE palavra_dia (
  id SERIAL PRIMARY KEY,
  palavra TEXT NOT NULL,
  criada_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE jogador (
  id SERIAL PRIMARY KEY,
  nome TEXT NOT NULL,
  criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE resultado (
  id SERIAL PRIMARY KEY,
  jogador_id INTEGER REFERENCES jogador(id),
  palavra_id INTEGER REFERENCES palavra_dia(id),
  tentativas INTEGER NOT NULL,
  tempo_seg INTEGER NOT NULL,
  criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);"""