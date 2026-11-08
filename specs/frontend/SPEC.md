# HOM-001 — Homologação do layout administrativo

Estado: VALIDATED no piloto local em 05/11/2026. Responsável: coordenação técnica.

## Objetivo e limites

AdminLTE 3 com páginas renderizadas no servidor, layout comum, navegação recolhível e seletor português/espanhol. A prova inicial evoluiu para o piloto com identidade Esther Beauty 777. Login e módulos comerciais possuem Specs próprias, com dados de demonstração.

## Contratos do recorte

Uma página inicial apresenta o painel fictício. A escolha de idioma aceita somente português e espanhol e persiste no navegador. Uma escolha inválida recai no idioma padrão proposto, português. Os mesmos templates atendem aos dois idiomas. Itens de módulos futuros aparecem apenas quando tiverem destino funcional. Recursos estáticos têm versões registradas e origem controlada.

## Critérios de aceite

| Caso | Resultado esperado |
| --- | --- |
| Desktop e celular | Cabeçalho e conteúdo legíveis, sem rolagem horizontal indevida. Menu pode abrir e fechar. |
| Navegação por teclado | Foco visível, ordem lógica e controles acessíveis por teclado. |
| Troca de idioma e recarga | Textos e atributo de idioma correspondem à escolha. A seleção persiste após recarregar. |
| Idioma inválido | A página retorna ao idioma padrão e continua navegável. |
| Rede e console | Recursos necessários carregam sem erro e a interface não gera erros no console. |
| Revisão de dependências | Registrar versão, origem, licença e risco dos componentes e testar compatibilidade. |

## Execução e retorno

Conferir disponibilidade de componentes MoviSys. Registrar a decisão de stack. Em seguida, montar o layout local, aplicar os catálogos de tradução, executar os casos de aceite e documentar os comandos de execução. O recorte é isolado e não realiza migração de dados. Se a integração falhar, registrar a evidência e rever a escolha antes de avançar para identidade.

Referências: [plano](../../docs/PLAN.md), [padrão AdminLTE](../../docs/frontend/ADMINLTE3_STANDARD.md) e [avaliação tecnológica](../../docs/architecture/technology-standard.md).

## Interface atual do piloto

### Ajuda guiada

Solicitação autorizada para abrir um manual lateral em português e espanhol, com exemplos e etapas interativas. A ajuda acompanha as permissões existentes. MASTER e DEV veem fluxos administrativos, o operador vê consultas, e manutenção aparece apenas para DEV. Cada assunto abre a tela correspondente e oferece uma sequência navegável com destaque e seta quando o controle estiver disponível. Os passos não executam ações do módulo. Validar rotas com e sem prefixo, teclado, foco, celular e filtragem por perfil.

A homologação inicial evoluiu para as telas dos módulos registrados no índice de Specs. A identidade visual da Esther Beauty 777 usa a logo fornecida, marfim, rosa e bronze, com AdminLTE 3.2 preservado. Login, estados de erro, menu lateral, botões contornados, formulários e relatórios compartilham o tema. O idioma autenticado usa POST com CSRF e preferência por conta. Os totais do painel vêm dos módulos, substituindo as quantidades fixas da prova inicial.
