from sqlalchemy import create_engine, Column, Integer, Boolean, Float, DateTime, Date, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("A variável de ambiente DATABASE_URL não foi definida.")

engine = create_engine(DATABASE_URL, echo=False)

Base = declarative_base()

class Minha_vida(Base):
    __tablename__ = "minha_vida"
    id = Column("id", Integer, primary_key=True, autoincrement=True)
    data = Column("data", DateTime, default=datetime.datetime.utcnow)
    nota_humor = Column("nota_humor", Float, nullable=True)
    secreto = Column("secreto", Boolean, nullable=True)
    Estudar = Column("Estudar", Boolean, nullable=True)
    Leitura = Column("Leitura", Boolean, nullable=True)
    Exercício_aerobico = Column("Exercício_aerobico", Boolean, nullable=True)
    Alimentação_saudavel = Column("Alimentação_saudavel", Boolean, nullable=True)
    Consumo_de_agua = Column("Consumo_de_agua", Boolean, nullable=True)
    Atencao_plena = Column("Atencao_plena", Boolean, nullable=True)
    Diario_e_fixacao = Column("Diario_e_fixacao", Boolean, nullable=True)
    Academia = Column("Academia", Boolean, nullable=True)
    Atividade_sexual = Column("Atividade_sexual", Boolean, nullable=True)
    data_hora_acordei = Column("data_hora_acordei", DateTime, nullable=True)
    data_hora_dormi = Column("data_hora_dormi", DateTime, nullable=True)
    Nota_humor_fim_dia = Column("Nota_humor_fim_dia", Float, nullable=True)
    status_conversa = Column(String, nullable=True)
    user_phone_number = Column(String, nullable=False)

    __table_args__ = (UniqueConstraint('user_phone_number', 'data', name='_user_date_uc'),)

    def __repr__(self):
        return f"<Minha_vida(id={self.id}, data={self.data})>"


class Habito(Base):
    """Definição de um hábito sim/não rastreável, por usuário.

    Substitui as colunas Boolean fixas da tabela minha_vida: adicionar um
    hábito é um INSERT aqui e congelar é set ativo=False (preservando o histórico).
    """
    __tablename__ = "habitos"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_phone_number = Column(String, nullable=False)
    nome = Column(String, nullable=False)
    categoria = Column(String, nullable=False)  # uma das 4 hipercategorias
    tipo = Column(String, nullable=False, default="sim_nao")  # reservado p/ futuro
    ativo = Column(Boolean, nullable=False, default=True)
    ordem = Column(Integer, nullable=False, default=0)
    emoji = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    registros = relationship("RegistroHabito", back_populates="habito", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint('user_phone_number', 'nome', name='_user_habito_uc'),)

    def __repr__(self):
        return f"<Habito(id={self.id}, nome={self.nome!r}, ativo={self.ativo})>"


class RegistroHabito(Base):
    """Lançamento diário de um hábito (sim/não) numa data."""
    __tablename__ = "registros_habito"
    id = Column(Integer, primary_key=True, autoincrement=True)
    habito_id = Column(Integer, ForeignKey("habitos.id"), nullable=False)
    data = Column(Date, nullable=False)  # data do calendário local (America/Sao_Paulo)
    valor = Column(Boolean, nullable=False)

    habito = relationship("Habito", back_populates="registros")

    __table_args__ = (UniqueConstraint('habito_id', 'data', name='_habito_data_uc'),)

    def __repr__(self):
        return f"<RegistroHabito(habito_id={self.habito_id}, data={self.data}, valor={self.valor})>"
