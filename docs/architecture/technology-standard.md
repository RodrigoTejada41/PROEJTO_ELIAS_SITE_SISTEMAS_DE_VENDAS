# Inventário e decisão tecnológica

## Confirmado em 03/11/2026

Diretório de trabalho vazio, inclusive na listagem de ocultos. Git informou que o diretório e seus pais não pertenciam a repositório. Sem código, módulos existentes, manifests, lockfiles, linguagens, frameworks, versões, ORM, migrações, autenticação, testes, CI, deploy, infraestrutura ou integrações identificados. Sem duplicação, acoplamento ou incompatibilidade existente verificável.

## Alternativas propostas

| Opção | Benefício | Custo e risco |
| --- | --- | --- |
| Python/FastAPI com páginas renderizadas no servidor e AdminLTE 3 | Uma implantação e um fluxo de navegação. REST/OpenAPI disponível conforme necessidade | Requer disciplina para manter regras fora de templates e delimitar componentes com JavaScript |
| Python/FastAPI com React/TypeScript e AdminLTE 3 | Estado tipado e componentes adequados a interações complexas | Build e dependências adicionais. Plugins que controlam DOM podem conflitar com React |
| ASP.NET Core com Razor e AdminLTE 3 | Templates tipados e ecossistema integrado para identidade e aplicações empresariais | Runtime e ferramentas diferentes da referência corporativa Python. Depende de capacidade da equipe |

Recomendação preliminar: validar a primeira opção, com PostgreSQL, SQLAlchemy e Alembic como candidatos. AdminLTE 3 é requisito explícito. Renderização no servidor difere da preferência corporativa React/Vite/Tailwind e depende de decisão registrada. A interface precisa provar navegação, tradução, foco e compatibilidade dos plugins. A carga, custo de hospedagem e versões suportadas serão verificados após autorização, antes de selecionar versões.

Sem dependências instaladas ou autorizadas para instalação nesta fase. Registrar finalidade, versão fixada, licença, suporte, riscos e responsável antes da adoção. Atualizar em homologação com análise de segurança, testes de regressão e retorno documentado. Adiar Redis, filas e serviços separados até existir requisito mensurável.

## Decisão de escopo HOM-001

Adotados Python 3.12, FastAPI 0.135.1, Jinja2 3.1.6 e Uvicorn 0.41.0 para a prova local, com versões diretas em requirements.txt. FastAPI e Jinja2 usam licença BSD-3-Clause. Uvicorn usa BSD-3-Clause. O banco continua em decisão para as próximas entregas. O benefício observado foi servir o painel em uma aplicação única, sem etapa de build do frontend.

## Estado implementado em 05/11/2026

Piloto em Docker Compose, PostgreSQL 18, Python 3.12 e dependências fixadas em requirements.txt. Interface Jinja2 com AdminLTE 3.2 e tema Esther Beauty 777. Migrações SQL têm histórico transacional e checksum. A decisão de Docker está no [ADR 0002](../adr/0002-docker-compose.md) e USD/PYG no [ADR 0003](../adr/0003-usd-pyg-commercial.md).
