# Retomada

DOC-001 · 2026-11-03 18:00 -03:00 · responsável: coordenação técnica.

Branch e commit indisponíveis. Escopo: inventário e documentação inicial. Referências: [estado](PROJECT_STATE.md), [Specs](../../specs/README.md), [inventário de arquivos](../REPORT.md) e [pendências](OPEN_ISSUES.md).

Etapa: revisão documental. Evidências: listagem inclusive de ocultos, verificação de Git e leitura da base normativa. Na retomada, listar arquivos, verificar Git e confrontar o plano com a origem do projeto. Próxima ação: obter autorização de implementação e fechar as decisões que condicionam o primeiro recorte.

Revisão documental concluída: 68 arquivos Markdown, inventário conferido e links locais válidos. Autorrevisão; build, testes de aplicação e validação de integração não aplicáveis nesta etapa.

## Continuação — 03/11/2026

Usuário autorizou continuar o projeto. Git ainda indisponível nesta pasta. Revisados o plano, o checkpoint e o padrão corporativo de recuperação. Atualizados o primeiro recorte local e a proposta de backup remoto. Próxima ação: registrar aprovação da stack e da Spec do recorte de homologação. Contratação e destino remoto seguem pendentes.

## Encerramento documental — 03/11/2026

HOM-001 está pronta para revisão, com limites, contratos, critérios verificáveis e sequência de execução. A implementação fica para a próxima etapa. O plano de backup descreve o piloto, e destino, retenção, RPO e RTO ficam como decisões operacionais. Na retomada, confirmar origem Git, revisar a Spec HOM-001 e registrar a decisão tecnológica antes de instalar dependências. Revisão documental pelo autor.

## HOM-001 — prova local executada

A instrução de continuar foi interpretada como autorização para executar apenas a prova local descrita. FastAPI com Jinja2 renderiza o layout AdminLTE 3 com dados fictícios. Idioma persiste em cookie e valores inválidos recaem em português. Verificados pip check, compilação Python, sintaxe JavaScript, HTTP dos arquivos estáticos e Edge via Playwright a 390 e 1280 px. Testados foco por Tab, menu por Enter, idioma após recarga, largura da página e ausência de erros de console ou respostas HTTP de erro. Revisão pelo autor. Revisão independente, auditoria completa e produção pendentes. Próximo recorte depende das decisões de identidade e acesso.

## Preparação de IDN-001

Specs de usuários e acesso detalhadas em DRAFT. Premissas propostas para o piloto: uma empresa, bootstrap local do MASTER e gestão de operadores exclusiva do MASTER. Consultado o padrão corporativo de segurança. A decisão de empresa única afeta a modelagem e deve ser registrada antes da implementação. Git continua indisponível. Próxima ação: confirmar o escopo de empresa e fechar a aprovação das Specs.

Identidade Esther Beauty 777 aplicada à HOM-001 com o JPEG fornecido. Edge validado a 390 e 1280 px, incluindo carregamento da logo, largura, teclado, menu, idioma e respostas HTTP.

## IDN-001 — bootstrap MASTER

Em 04/11/2026, a continuação foi interpretada como autorização para avançar no piloto local com uma empresa. Criados migrations/001_identity.sql e app/bootstrap_master.py. PostgreSQL foi escolhido para manter o padrão corporativo. O índice parcial garante unicidade do MASTER e a criação e auditoria usam a mesma transação. Verificados pip check, compileall, ajuda do comando e teste simulado de validação, hash Argon2id, auditoria e conflito. PostgreSQL real e concorrência não validados: psql e serviço local não encontrados, Docker Desktop sem engine acessível. Revisão pelo autor. Próximo passo: executar a migração e testar concorrência em PostgreSQL isolado, depois integrar login e sessões.

## IDN-001 — teste reproduzível de concorrência

Criado tests/test_bootstrap_integration.py. O teste aplica a migração em esquema descartável e verifica duas tentativas concorrentes, um único MASTER, o hash da senha e um único registro de auditoria. compileall passou. unittest descobriu o caso e pulou a execução sem IDENTITY_TEST_DSN. Após iniciar Docker Desktop, o motor Linux retornou HTTP 500. Falta executar em PostgreSQL descartável antes de registrar a validação da migração e da concorrência.

## IDN-001 — validação em PostgreSQL

Em 04/11/2026, a migração 001 e o teste de integração passaram em PostgreSQL 18.6 temporário no Windows, com acesso restrito ao loopback. O teste executou duas tentativas concorrentes e verificou uma única conta MASTER, a validade do hash Argon2id e um único evento de auditoria associado à conta. O teste removeu seu esquema e a instância foi encerrada. Git segue indisponível nesta pasta. A Spec de usuários segue em DRAFT. Próximo passo: aprovar o recorte de login e sessões antes da implementação.

## IDN-001 — login e sessões do piloto

Aprovação explícita recebida em 04/11/2026 para login e sessões de uma empresa. A migração 002 cria sessões revogáveis e limite de tentativas em PostgreSQL. Login e logout em português e espanhol, proteção do painel, CSRF em formulários, rotação de sessão e auditoria de login e logout foram implementados. Decisões do piloto: oito horas de sessão e cinco tentativas por IP em cinco minutos.

Em PostgreSQL 18.6 temporário, passaram os três testes, incluindo bootstrap concorrente e fluxo ASGI com cookies HTTPS, senha incorreta, usuário desconhecido, limite, CSRF, rotação, conta inativa, expiração e logout. pip check e compileall passaram. Instância encerrada. Git indisponível. Revisão pelo autor. Validação visual em navegador e revisão independente pendentes. Recuperação e gestão de operadores seguem em recortes próprios.

## IDN-001 — verificação no navegador

Em 04/11/2026, Playwright com Edge e PostgreSQL descartável validou login e painel a 390 e 1280 px. Verificados foco por Tab, envio por Enter, idioma persistente após recarga, ausência de rolagem horizontal, logout e redirecionamento ao tentar voltar ao painel. Corrigido o 404 inicial do favicon do login seguindo o padrão do painel. Reexecução em sessão nova passou sem erros de console, JavaScript ou respostas HTTP de erro no fluxo. Revisão independente segue pendente.

## IDN-001 — recuperação local do MASTER

Continuação de 04/11/2026 registrada como aprovação do recorte de recuperação. Comando local com senha sem eco, validação compartilhada com bootstrap e troca Argon2id. Migração 003 registra o papel PostgreSQL responsável. Alteração da senha, revogação e auditoria na mesma transação. Login usa bloqueio compartilhado da conta para coordenar criação de sessão com a recuperação.

Em PostgreSQL 18.6 descartável, três testes passaram. Validados duas sessões revogadas, rejeição da senha antiga, acesso com a nova senha, auditoria e login concorrente com a recuperação. pip check, compileall e ajuda do comando passaram. Prompt interativo em terminal e revisão independente pendentes. Git indisponível. Próximo recorte: gestão de operadores, após aprovação da Spec correspondente.

## IDN-001 — gestão de operadores

Continuação de 04/11/2026 registrada como aprovação da gestão de operadores no piloto. MASTER lista, cria e desativa operadores na interface em português e espanhol. Rotas verificam sessão, papel e CSRF. Desativação é idempotente, revoga todas as sessões do alvo e registra o MASTER responsável na mesma transação, usando a migração 004.

Quatro testes passaram em PostgreSQL 18.6, incluindo acesso direto, elevação de papel, CSRF, duplicidade, preservação do MASTER e revogação. pip check e compileall passaram. Edge validou cadastro e desativação a 390 px em português e a 1280 px em espanhol, com teclado, sem rolagem horizontal nem erros de console ou HTTP. Ambiente temporário encerrado. Revisão independente pendente e Git indisponível. Próximo recorte comercial depende da aprovação da respectiva Spec.

## CAT-001 — proposta para revisão

Em 04/11/2026, detalhado o primeiro recorte comercial na Spec de produtos. Premissas propostas: um registro por SKU, MASTER administra o catálogo e operador consulta itens ativos. Preços e estoque ficam para recortes próprios. Consultados os padrões corporativos de Spec e banco. Git indisponível nesta pasta. Próxima ação: aprovar a Spec de catálogo antes da implementação.

## CAT-001 — catálogo do piloto

Continuação de 04/11/2026 registrada como aprovação da CAT-001. Migração 005, listagem com busca, cadastro, edição com versão e inativação auditada. MASTER administra SKUs e operadores consultam ativos. Cinco testes passaram em PostgreSQL 18.6, incluindo concorrência de código, código de barras com zero inicial, autorização, CSRF, conflito de edição e rollback de auditoria. pip check e compileall passaram. Edge validou cadastro, edição e inativação com teclado a 390 px em português e a 1280 px em espanhol, sem erros HTTP ou de console. Git indisponível e revisão independente pendente.

Prévia local de demonstração em http://127.0.0.1:64693/ com PostgreSQL temporário no loopback e dados fictícios. Credencial de demonstração entregue na conversa. Próximo recorte comercial requer sua própria Spec.

## Identidade visual no login

Em 04/11/2026, aplicado ao login o tema da Esther Beauty 777, com logo existente, paleta do painel e foco visível. Edge validou carregamento da logo e recursos, português e espanhol, navegação por Tab e ausência de rolagem horizontal a 320 e 1280 px. Prévia local atualizada.

## Retomada em 05/11/2026

Disco e documentação conferidos. Git segue indisponível. Restaurados PostgreSQL temporário e servidor da prévia em http://127.0.0.1:64693/ com os cinco SKUs fictícios existentes. Elaborada a Spec EST-001 em revisão. Premissas propostas: local único, unidades inteiras, MASTER movimenta e operador consulta, saldo não negativo e repetição idempotente. Próxima ação: aprovar a Spec antes da implementação. Revisão independente pendente.

## Docker e EST-001 — 05/11/2026

Docker Desktop 29.9.1 e Compose 5.6.0 disponíveis. Criados Dockerfile, Compose, secret PostgreSQL local, volume persistente e executor transacional de migrações com checksum e bloqueio. Arquitetura registrada em docs/adr/0002-docker-compose.md e operação em docs/deployment/DOCKER.md. O contexto de build exclui segredos e arquivos locais.

Os dados fictícios da prévia Windows foram copiados por pg_dump e restaurados no PostgreSQL Docker. Mantida a conta master-demo com sua credencial existente. Novo endereço http://127.0.0.1:8765/.

A instrução de continuar após Docker foi registrada como aprovação da EST-001. Implementados entrada, saída, compensação única por movimento, saldo não negativo, controle de concorrência por SKU, idempotência e histórico paginado. Limites adotados: 1 bilhão por movimento e saldo até 2 bilhões. MASTER movimenta e operador consulta SKUs ativos. Unidades inteiras e local único conforme proposta.

Sete testes passaram no container, incluindo concorrência de saídas, repetição simultânea, compensação, rollback, inativação concorrente, autorização e migrações. pip check e compileall passaram. Edge verificou entrada, saída e compensação em português a 390 px e espanhol a 1280 px, com teclado, saldo 7, logout e ausência de erros de console ou HTTP. Revisão independente pendente. Git continua indisponível.

Verificação final: backup completo restaurado em banco descartável com cinco SKUs, seis migrações e saldo demonstrativo 7. Bancos de restauração removidos após conferência. Containers reiniciados com dados preservados e healthchecks saudáveis. Aplicação UID 10001, segredo fora da imagem e HTTP 200 no login com identidade visual. Prévia Windows encerrada, dados originais preservados no disco e backups em .local ignorada pelo Git. Endereço vigente http://127.0.0.1:8765/.

## Continuação comercial e validação — 05/11/2026

Autorização ampla recebida para entregar o máximo de Specs, interrompendo apenas por autorização especial ou definição indispensável. Usuário definiu USD e guarani, custo/preço atrelados ao dólar e comissão percentual ajustável. Implementados clientes, fornecedores, relatório de estoque/CSV, auditoria administrativa, financeiro, preços e custos, câmbio, vendas, comissões, relatórios monetários e preferência de idioma por conta.

Regras do piloto: MASTER administra módulos comerciais e operador consulta catálogo/preços sem custos, clientes e estoque ativos e relatório de estoque. Eventos de comissão e percentual exigem seleção explícita. A regra é versionada e preservada na venda. Câmbio comercial inicia manual, com referência automática selecionável. O worker Docker verifica o provedor respeitando sua publicação diária. BCP automatizado retornou HTTP 403; ExchangeRate-API foi consultada de fato e identificada na interface. Não presumir atualização de mercado em tempo real.

Vinte e dois testes passaram no Docker. Cobertos contatos/versão/duplicidade, autorização, segredo suprimido na auditoria, CSV protegido, relatórios, múltiplas moedas, precisão, baixas parciais, pagamentos concorrentes, estorno, snapshots de venda/câmbio/percentual, estoque e reversões, comissão paga seguida de estorno e locale persistido. pip check, compileall e sintaxe JavaScript verificados.

Edge validou o fluxo completo em banco separado a 390 e 1280 px, PT/ES: logo e navegação, cliente e fornecedor, preços/custos, estoque, venda com desconto, recebimento PYG em título USD, comissão percentual, pagamento, estorno após pagamento, cancelamento com estoque restaurado, relatórios e download CSV, idioma e acesso negado localizado para operador. Recuperação do MASTER validada em terminal Docker real, com duas entradas sem eco, apenas no banco de homologação.

Git local inicializado conforme regra do projeto. Não existe histórico anterior para comparação. Segredos, dumps e ambiente local são ignorados e excluídos do contexto da imagem. Revisão pelo autor; revisão independente pendente. Endereço principal http://127.0.0.1:8765/. A conta de demonstração do banco principal foi preservada. Próximas decisões operacionais: cotação comercial e evento/percentual por vendedor na interface, VPS/domínio/TLS e backup operacional antes de dados reais.

## Fechamento da continuação — 05/11/2026

Confirmados 22 testes no pacote final, pip check, compilação e sintaxe JavaScript. A checagem de whitespace considerou CRLF como final de linha válido para preservar os checksums de migração. Setenta e dois Markdowns e seus links locais foram conferidos.

Ajuste final de busca móvel e identificação do provedor no relatório com cotação automática passaram no Edge. Container e banco isolados de QA foram removidos após os testes. Backup final em .local/esther-pilot-verified.dump restaurado em banco descartável com 13 migrações, cinco SKUs e um MASTER; banco de restauração removido após conferência. Login e logout da demonstração principal continuam válidos. Aplicação, banco e worker de câmbio seguem no Compose do projeto.

## Confirmação e referência oficial — 05/11/2026

Recebida definição do usuário: comissão na confirmação e referência USD/PYG oficial automática. A interface grava novas regras no evento de confirmação, com percentual ajustável. Não havia regras cadastradas na demonstração. Migração 014 aplicada, worker Docker passou a consultar diretamente a tabela diária do BCP e ativou a referência oficial de 05/11/2026. Acesso no host retornou 403; a consulta e extração dentro do Docker passaram. Taxas antigas permanecem no histórico. Revisão independente pendente.

## Verificação operacional da migração 014

Backup local em .local/esther-014.dump. Restauração concluída em banco descartável, removido após a conferência. Confirmadas 14 migrações, cinco SKUs, zero regras de comissão e política automática com referência BCP de 05/11/2026. SHA-256 D051E18D2C2F18E3C77354DFE92030A7189FA57C01C22570FA867A720AE60F54. Pendências vigentes consolidadas em OPEN_ISSUES.md.

## CAT-002 — Importação e foto no catálogo

O pedido de importar produtos por planilha e adicionar imagens autorizou o recorte CAT-002. O MASTER baixa o modelo, importa novos SKUs por CSV UTF-8 e pode anexar, trocar ou remover uma foto na edição. A importação inteira é revertida em caso de duplicidade. A foto é armazenada no PostgreSQL pela migração 015.

O build Docker, o pip check e os 24 testes passaram. Edge validou download, importação e envio de foto com teclado em PT a 390 px e ES a 1280 px, em banco separado. Backup pré-migração em .local/esther-before-catalog-015.dump com catálogo do dump legível. Prévia local atualizada e saudável em http://127.0.0.1:8765/, com 15 migrações e cinco SKUs de demonstração. Revisão independente e operação em produção seguem em aberto.

## VEN-002 e IDN-002 — 07/11/2026

Usuário aprovou dados da empresa, recibo simples sem emissão fiscal e perfil DEV acima do MASTER. Migração 016 registra a ficha de empresa única, o emissor original de cada recibo e a unicidade do DEV. A manutenção exige reautenticação do DEV para redefinir a senha do MASTER, revoga as sessões afetadas e registra o ator. O provisionamento do DEV é feito em terminal interativo e está descrito no README.

Os 26 testes passaram em PostgreSQL, com emissão concorrente, reimpressão após edição da ficha, bloqueio por estado da venda, permissões e revogação. Edge confirmou cadastro e impressão em PT a 390 px e ES a 1280 px, com teclado, geração de PDF e sem erros de console ou HTTP nos fluxos verificados. Compilação Python, sintaxe do JavaScript e pip check passaram.

Backup pré-migração em .local/esther-before-administration-016.dump. A restauração em banco descartável recuperou 15 migrações. A atualização dessa cópia para 016 manteve os cinco SKUs. Revisão independente pendente.

## CAT-003 — Planilha Excel do catálogo

Usuário aprovou tabela XLSX vazia ou preenchida, preços base em USD e atualização de produtos pela mesma planilha. A exportação administrativa usa lotes de até 1.000 produtos e calcula PYG pela cotação comercial. A confirmação revalida os dados e a versão de cada SKU em uma transação. O CSV anterior continua disponível. O recorte reutiliza os campos e a auditoria existentes, sem migração de banco.

O build Docker, a compilação, o pip check e 28 testes passaram. Edge validou download, prévia e layout em PT a 390 px e ES a 1280 px, incluindo confirmação de preço em USD e novo download com PYG recalculado em banco isolado. A estrutura XLSX foi reaberta e conferida de forma automatizada. Microsoft Excel desktop e revisão independente pendentes.

## VEN-003 — Venda dinâmica e homologação local

Usuário aprovou a venda em tela única e solicitou homologação dos fluxos. Pesquisa por código, descrição ou código de barras com foto, preço e saldo. A tela mantém a lista até salvar o rascunho ou confirmar. A confirmação preserva a transação comercial existente. O recibo usa somente a estrutura visual da referência e abre o diálogo de impressão do navegador. Nenhuma migração foi necessária.

Aprovados 29 testes PostgreSQL. Edge validou venda e recibo em PT a 390 px e ES a 1280 px. A homologação em banco descartável cobriu navegação, cadastro, estoque, contatos, importações, financeiro, comissões, relatórios e perfis. Corrigido HTTP 405 na troca de idioma após erro de formulário. Evidências e limites no [relatório](../REPORT.md#homologação-local--ven-003-e-fluxos-do-piloto).

## EST-002 — Estoque negativo global e entradas por Excel

Usuário aprovou a opção global e entradas em lote pela planilha exportada do banco. A migração 017 inclui configuração desmarcada por padrão, trilha de alterações e controle idempotente de lotes. Saídas de venda, manuais e compensações consultam a mesma política. Desligar a opção permite recuperar saldos negativos gradualmente. Cada arquivo registra um lote e a confirmação revalida o saldo corrente, preservando o histórico por SKU.

Build Docker e 32 testes PostgreSQL passaram. Edge validou configuração, download, prévia, gravação e histórico em português a 390 px e espanhol a 1280 px. O exemplo de −3 com entrada de 10 gravou saldo 7. Backup pré-migração em .local/esther-before-inventory-017.dump restaurado em banco descartável, que recebeu a migração 017 com a opção desmarcada e cinco SKUs preservados. Excel desktop e revisão independente pendentes.

## Ajuste visual do recibo

O recibo usa o logotipo próprio da Esther Beauty 777 junto ao nome preservado na emissão. Cabeçalho, dados da venda, grade e totais receberam espaçamentos e bordas consistentes. Edge carregou o logotipo a 390 px em PT e a 1280 px em ES. PDFs A4 de uma e duas páginas foram gerados com cabeçalhos e total presentes. Impressora física pendente.

## REL-003 — Painel de vendas e filtros gerenciais

Usuário aprovou o painel de vendas no início e os filtros de relatórios. MASTER e DEV consultam vendas confirmadas, ticket médio, tendência e ranking. O equivalente PYG soma a conversão pela taxa preservada em cada venda. As abas compartilham os filtros relevantes. Estoque filtra saldo positivo, zero e negativo. O fluxo financeiro filtra recebimentos, pagamentos ou estornos e totaliza por moeda. Operador mantém acesso ao estoque ativo. Sem migração.

Build Docker, compilação e 32 testes PostgreSQL passaram. Edge validou em PT a 390 px e ES a 1280 px a passagem dos filtros entre painel, vendas e ranking, o CSV filtrado, o estoque negativo e a seleção de natureza financeira. Revisão independente pendente.

## SEC-001 — Preparação de segurança para VPS

Em 08/11/2026, preparado o complemento Compose para produção, com credenciais separadas de administração, migração, aplicação e worker. A migração aplica os privilégios na mesma transação. O Uvicorn confia apenas no IP informado do proxy. O procedimento e os critérios de publicação estão em [Docker](../deployment/DOCKER.md).

Validada a resolução dos dois arquivos Compose. PostgreSQL descartável aplicou as 17 migrações e repetiu a execução, executou o worker com referência simulada e bloqueou DDL pela aplicação e leitura de senhas pelo worker. A suíte existente passou com 32 testes em PostgreSQL descartável. Teste ASGI verificou IP, esquema, cookie Secure e cabeçalhos de uma origem não confiável. O pip-audit não encontrou vulnerabilidades conhecidas nas dependências resolvidas na consulta. Docker Engine inacessível no host. Build e varredura das imagens, validação no proxy real, backup externo e revisão independente pendentes.

O remoto origin foi configurado e respondeu por SSH. O GitHub já tem histórico em main. A branch local master segue sem commit. A publicação precisa reconciliar as duas origens.

## ACE-002 — Verificação em duas etapas

Em 08/11/2026, implementado login em duas etapas com aplicativo autenticador. A migração 018 adiciona segredos cifrados, desafios de cinco minutos e marcação de sessões verificadas. O complemento Compose exige o fator para todos os perfis. Contas sem cadastro continuam acessíveis no piloto, fora do modo obrigatório. Cadastro e substituição ocorrem por terminal privado e revogam sessões. Instruções de geração, custódia e restauração da chave em [Docker](../deployment/DOCKER.md#verificação-em-duas-etapas).

Passaram 35 testes em PostgreSQL descartável, incluindo vetor RFC 6238, fluxo ASGI com CSRF, desafio sem acesso ao painel, expiração, bloqueio, código reutilizado e troca de senha. Um teste separado executou as 18 migrações e o cadastro, login e substituição auditada com os papéis de produção. Compilação, pip check, resolução do Compose e pip-audit passaram. Docker Engine local indisponível. Validação visual em navegador, build da imagem, teste com dispositivo real, proxy da VPS e revisão independente pendentes.

### Primeiro acesso com Google Authenticator

A migração 019 adiciona a ativação por código de uso único emitido em terminal privado. O código vale 24 horas. O usuário informa senha e ativação no primeiro acesso, escaneia o QR Code gerado localmente ou usa a chave manual e confirma um TOTP para abrir a sessão. O QR é vinculado ao desafio de cinco minutos. A confirmação consome a ativação e registra auditoria. Contas já cadastradas continuam no fluxo de senha e TOTP.

Passaram 36 testes em PostgreSQL descartável, incluindo os quatro de MFA que cobrem a ausência do QR antes da ativação, resposta sem cache, confirmação do código e consumo da ativação. A compilação, a resolução do Compose e o pip-audit passaram. Docker Engine inacessível e leitura do QR pelo Google Authenticator em aparelho real pendente.
