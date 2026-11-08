# control_de_ventas

Gestão comercial e administrativa web para Esther Beauty 777, por MoviSys Tecnologia. Piloto Docker com identidade, catálogo, USD/PYG, estoque, clientes, fornecedores, vendas, financeiro, comissões e relatórios.

- [Visão e escopo](docs/product/PROJECT_OVERVIEW.md)
- [Arquitetura](docs/architecture/SYSTEM_ARCHITECTURE.md)
- [Inventário e decisão tecnológica](docs/architecture/technology-standard.md)
- [Plano e tarefas](docs/PLAN.md)
- [Specs](specs/README.md)
- [Retomada](docs/memory/RESUME_POINT.md)
- [Relatório e inventário de arquivos](docs/REPORT.md)

## Executar com Docker

Consulte [Docker local e preparação para VPS](docs/deployment/DOCKER.md). Com o secret local preparado, execute:

```powershell
docker compose up -d --build --wait
```

Acesse http://127.0.0.1:8765/. A aplicação e o banco executam em containers e o PostgreSQL usa volume persistente.

## Executar HOM-001 no Windows

No PowerShell, na raiz do projeto, com Python 3.12:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Configure o banco e provisione o MASTER conforme a seção abaixo. Abra http://127.0.0.1:8765/ e entre com a conta criada. O painel usa dados fictícios e recursos estáticos locais.

## Provisionar o primeiro MASTER em desenvolvimento

Em um banco PostgreSQL dedicado ao projeto, configure a conexão com as variáveis padrão do libpq (PGHOST, PGPORT, PGDATABASE e PGUSER). Forneça a credencial do banco pelo mecanismo local de segredos. Com essas variáveis configuradas, execute as migrações rastreadas e execute o comando em um terminal interativo:

```powershell
.venv/Scripts/python -m app.migrate
.venv/Scripts/python -m app.bootstrap_master nome-do-master
```

A senha da conta é solicitada no terminal. O executor aplica as migrações pendentes e verifica checksum. Banco legado sem histórico exige conferência antes da adoção. O servidor web usa as mesmas variáveis de conexão. O piloto limita a cinco tentativas de login por endereço em cinco minutos. A sessão dura até oito horas e o logout a revoga no banco.

### Recuperar a senha do MASTER

Aplique a migração 003 e execute em um terminal local autorizado, com as variáveis libpq apontando para o banco correto e credenciais administrativas:

```powershell
.venv/Scripts/python -m app.recover_master
```

Digite e confirme a nova senha sem eco. A operação revoga todas as sessões do MASTER e registra o papel PostgreSQL que executou a recuperação. Quando o papel é compartilhado, o evento identifica o papel usado e a identificação individual depende dos controles de acesso do ambiente.

### Gerenciar operadores

Aplique a migração 004. Entre como MASTER e abra **Operadores** no menu para cadastrar ou desativar contas de operador. A desativação encerra suas sessões e impede novos logins.

### Configurar a empresa e imprimir recibos

Com a migração 016 aplicada, entre como MASTER ou DEV e abra **Dados da empresa** no menu. Preencha o nome que deve aparecer no recibo e, se aplicável, nome comercial, RUC, endereço e telefone.

Abra uma venda confirmada e selecione **Imprimir recibo**. A página oferece impressão e salvamento em PDF pelo navegador. O recibo é sem valor fiscal e registra a venda. A quitação é registrada no financeiro. A primeira emissão guarda os dados da empresa para reimpressão.

### Criar a conta de manutenção DEV

Em um terminal local autorizado, na raiz do projeto com o Compose ativo, execute:

```powershell
docker compose exec app python -m app.container_entrypoint python -m app.bootstrap_dev nome-do-dev
```

Escolha uma senha própria de 15 a 128 caracteres no terminal. A conta DEV tem os acessos administrativos do MASTER e a área **Manutenção DEV**, onde pode redefinir a senha do MASTER e encerrar as sessões existentes após confirmar a própria senha.

### Usar o catálogo

Aplique a migração 005 e abra **Catálogo** no menu. MASTER pode cadastrar, editar e inativar SKUs. Operadores consultam SKUs ativos.

Em **Catálogo → Importar produtos**, MASTER e DEV podem baixar o modelo Excel vazio ou exportar os produtos atuais em lotes de até 1.000 linhas. Edite os dados e valores em USD, mantenha os códigos como texto e use **Conferir planilha** antes de confirmar. Os valores PYG da exportação são calculados pela cotação comercial e ficam disponíveis para consulta. Dados inválidos, duplicados ou alterados no sistema desde a exportação impedem a gravação do lote. O limite por arquivo XLSX é de 1 MiB.

O fluxo CSV UTF-8 continua disponível para novos cadastros. Para anexar uma foto, encontre o SKU, abra **Editar** e use **Salvar foto**. A foto acompanha o backup do PostgreSQL.

### Movimentar estoque

Abra **Estoque** e selecione um SKU. MASTER e DEV registram entradas, saídas e compensações com motivo. Operadores consultam saldo e histórico. Em **Configurações de estoque**, MASTER e DEV podem permitir estoque negativo para todos os produtos. A opção começa desligada.

Em **Estoque → Importar entradas**, baixe o Excel preenchido com produtos ativos e saldos, informe **Quantidade a adicionar** e o motivo do lote, confira a prévia e confirme. As quantidades somam ao saldo efetivo no momento da gravação. Cada arquivo só registra um lote. Baixe um arquivo novo para outra entrada.

### Testar identidade, acesso, catálogo e estoque

Configure IDENTITY_TEST_DSN com a conexão a um banco PostgreSQL descartável. A conta de teste precisa poder criar esquemas. O teste aplica a migração em um esquema de nome aleatório e remove esse esquema ao terminar.

```powershell
.venv/Scripts/python -m unittest discover -s tests -v
```

## Fluxo do piloto

1. Em **Câmbio**, confira a referência oficial USD/PYG que o worker consulta a cada hora.
2. Em **Preços e custos**, informe os valores base em USD. O equivalente em PYG acompanha a taxa comercial. Custos são exclusivos do MASTER.
3. Cadastre clientes e fornecedores e registre as entradas físicas em **Estoque**.
4. Em **Comissões**, defina o percentual por vendedor. A apuração ocorre na confirmação da venda.
5. Em **Vendas → Nova venda**, busque produtos por nome, código ou código de barras e adicione os itens na mesma tela. Ajuste quantidades, preços e desconto. Salve como rascunho ou confirme para registrar estoque, conta a receber e comissão do evento configurado. Na venda confirmada, **Imprimir recibo** abre a opção de escolher uma impressora ou salvar em PDF.
6. Em **Financeiro**, registre baixas parciais em USD ou PYG. Cada conversão preserva valor e taxa.
7. Para corrigir uma venda recebida, estorne o recebimento antes de cancelar a venda. Comissões e estoque mantêm suas reversões rastreáveis.
8. Consulte **Relatórios** e **Auditoria**. O fluxo financeiro separa moedas, baixas e estornos.

A preferência PT/ES é salva na conta pela interface. Relatórios oferecem CSV com filtros e limite explícito de exportação. O ambiente principal contém dados de demonstração. Consulte o [índice de Specs](specs/README.md) para limites e validação de cada recorte.

No **Painel administrativo**, MASTER e DEV podem filtrar o resumo de vendas por período e vendedor. Em **Relatórios**, as abas dão acesso às vendas confirmadas, ranking de produtos, posição de estoque por faixa de saldo e fluxo financeiro por moeda e tipo de movimento. O período padrão do painel é de 30 dias. O total em guaranis usa a cotação registrada em cada venda.

## Validação

A suíte de integração executa em esquemas PostgreSQL descartáveis. A verificação visual usa um banco separado para preservar a demonstração principal. Comandos Docker em [operação](docs/deployment/DOCKER.md). Evidências no [checkpoint](docs/memory/RESUME_POINT.md).
