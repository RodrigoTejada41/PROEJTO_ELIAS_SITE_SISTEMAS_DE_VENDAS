# Plano proposto

1. Aprovar escopo inicial, país, moeda, estrutura empresarial e matriz de acesso.
2. Verificar componentes MoviSys reutilizáveis e escolher stack, dependências e hospedagem. Validar AdminLTE 3 em prova autorizada e registrar decisão.
3. Revisar e aprovar Specs de identidade, acesso, empresa, idioma e auditoria. Modelar dados e critérios de bootstrap e recuperação.
4. Planejar catálogo, clientes, fornecedores e estoque. Definir integridade, migrações e testes transacionais.
5. Definir contratos de venda, financeiro e comissões. Validar confirmação, retry, concorrência e estorno antes de fechar o plano de implementação.
6. Fechar relatórios e operação. Definir aceite, restauração, homologação e rollback.

Continuação autorizada em 03/11/2026. A escolha da stack e o aceite do primeiro recorte permanecem pendentes. Começar pelo recorte abaixo antes de iniciar módulos comerciais.

## Primeiro recorte proposto — homologação local

- **Stack candidata:** FastAPI, páginas renderizadas no servidor, AdminLTE 3 e PostgreSQL. Confirmar versões, suporte, licença e compatibilidade antes de instalar.
- **Entrega:** layout administrativo responsivo com navegação por teclado e seleção português/espanhol, sem dados reais. Provar integração visual e documentar como executar localmente.
- **Aceite:** renderização em desktop e celular, troca de idioma no mesmo layout, foco visível, recursos estáticos carregados e console sem erros. Registrar versões e evidências.
- **Depois:** implementar identidade e controle de acesso após decidir empresa única ou múltipla, bootstrap do MASTER e matriz de permissões. Antes de dados reais, validar a recuperação remota conforme o plano de backup.

### Sequência de implementação de HOM-001

1. Registrar a decisão tecnológica e revisar os critérios da [Spec HOM-001](../specs/frontend/SPEC.md).
2. Preparar execução local e layout, integrar o tema provisório e os catálogos de idioma.
3. Validar em desktop e celular, registrar evidências e revisar dependências e licenças.
4. Usar o resultado para fechar as Specs de identidade e acesso. Aprovar o piloto com dados reais somente após validar a restauração independente.

## Próximo recorte comercial — CAT-001

Submeter a [Spec de catálogo](../specs/products/SPEC.md) à aprovação. Após aceite, implementar migração e autorização, cadastrar e consultar SKUs, adicionar edição com controle de versão e inativação auditada. Validar no PostgreSQL descartável e no navegador. Estoque e vendas poderão referenciar o ID estável do SKU após aprovação de seus próprios contratos.

## Situação em 05/11/2026

HOM-001, identidade e CAT-001 foram implementados e verificados no piloto local, conforme checkpoint. Stack em uso: FastAPI, Jinja2, AdminLTE 3 e PostgreSQL. As referências acima à stack candidata descrevem o planejamento inicial.

Próximo recorte proposto: [EST-001](../specs/inventory/SPEC.md), com entrada e saída administrativa por SKU, saldo não negativo, histórico e idempotência. A proposta precisa de aprovação das regras de quantidade inteira, local único e acesso por papel antes da implementação.

## Entrega em 05/11/2026

Ambiente Docker e EST-001 implementados no piloto. Evidências e limites no checkpoint. Operação local e preparação da VPS em [Docker](deployment/DOCKER.md). O próximo recorte comercial será detalhado nas Specs de clientes, fornecedores e preços, conforme a sequência acima.

## Continuação ampla — 05/11/2026

Usuário autorizou concluir o máximo de Specs e implementar seus recortes de piloto, parando apenas por autorização especial ou definição indispensável. Sequência desta continuação: clientes, fornecedores, relatórios de estoque e consulta de auditoria. Moeda e política de comissão foram solicitadas para fechar os recortes monetários. Compartilhar os helpers HTTP existentes entre módulos, preservando seus contratos e a stack.

## Entrega dos recortes comerciais — 05/11/2026

Consolidados CLI-001, FOR-001, CAM-001, VEN-001, FIN-001, COM-001, REL-001/002, AUD-001 e LOC-001, além dos recortes existentes de identidade, catálogo, estoque e frontend. Matriz ACE-001 descreve os acessos implementados. Evidências no checkpoint. Parâmetros comerciais explícitos ficam disponíveis nas telas de câmbio e comissões. Publicação em VPS continua etapa de implantação com destino e autorização próprios.

## VEN-002 e IDN-002 — 07/11/2026

Implementação aprovada pelo usuário. Aplicar migrações aditivas para ficha, recibo e perfil DEV. Usar o controle administrativo comum para DEV e MASTER, com manutenção exclusiva do DEV. Verificar os fluxos em esquemas PostgreSQL descartáveis antes de atualizar a prévia local. Retorno operacional descrito nas Specs.
