# Arquitetura proposta

Um monólito modular reúne apresentação, aplicação, domínio e persistência. O navegador acessa a aplicação por HTTPS. A apresentação invoca casos de uso, que aplicam regras e autorização e acessam persistência por fronteiras do módulo. A API, quando necessária, usa REST/OpenAPI e erros com correlação. Integrações entram por adaptadores próprios.

Uma venda confirmada deve produzir efeitos coerentes sobre estoque, financeiro e comissões. Proposta inicial: coordenar contratos internos e escrita transacional no mesmo banco, com chave de idempotência e reversões rastreáveis. Validar os gatilhos comerciais antes da modelagem. Dados monetários exigem precisão decimal e regra explícita de arredondamento.

O diagnóstico parte de um diretório vazio. [Limites](MODULE_BOUNDARIES.md) e [dependências](DEPENDENCY_MAP.md) descrevem desenho inicial.
