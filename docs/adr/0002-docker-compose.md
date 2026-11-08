# 0002 — Ambiente local em Docker Compose

Data de aprovação: 05/11/2026, por solicitação explícita do usuário.

Manter Python 3.12, FastAPI, Jinja2 e PostgreSQL. Empacotar a aplicação em imagem Linux com usuário sem privilégios. Compose coordena banco persistente, migração com registro e aplicação em porta local. Senha PostgreSQL em arquivo de secret ignorado pelo Git e pelo contexto de build.

O ambiente existente no Windows será preservado durante a validação. Preferir transferir a demonstração por backup e restauração PostgreSQL quando a conexão ao host estiver disponível. Banco do Docker usa volume nomeado próprio. Migrações SQL existentes serão executadas transacionalmente com histórico e checksum. Banco legado sem histórico exige adoção explícita após conferir estrutura e migrações.

Alternativa avaliada: manter processos manuais do Windows. Docker foi escolhido para reproduzir o ambiente Linux na futura VPS. Implantação na VPS ainda exige destino, domínio, HTTPS, segredos, backup e autorização de publicação.

Validar build, healthchecks, migrações repetidas, testes PostgreSQL, login HTTP e preservação do volume. Retorno local utiliza a prévia anterior. Não remover o volume para retornar.
