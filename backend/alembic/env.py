from logging.config import fileConfig

from alembic import context
from app import models  # noqa: F401  (registra as tabelas no metadata)
from app.db import Base, criar_engine

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _url() -> str:
    # Testes podem injetar outra URL via config; padrão vem das settings do app.
    return config.attributes.get("url") or criar_engine().url.render_as_string(hide_password=False)


def run_migrations_offline() -> None:
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = criar_engine(_url())
    with connectable.connect() as connection:
        if connection.dialect.name == "sqlite":
            # batch_alter_table recria tabelas (copia, apaga, renomeia): com FK ligada, apagar uma tabela
            # referenciada (ex.: ativo) falha. Procedimento recomendado pelo SQLite; conferido no fim.
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
            connection.commit()
        context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()
            if connection.dialect.name == "sqlite":
                violacoes = connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
                if violacoes:
                    raise RuntimeError(f"Migração deixou chaves estrangeiras inválidas: {violacoes[:5]}")


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
