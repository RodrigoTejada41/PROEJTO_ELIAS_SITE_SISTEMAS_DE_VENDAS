# Specs do piloto Esther Beauty 777

A autorização ampla de 05/11/2026 permitiu entregar os recortes abaixo. VALIDATED indica verificação do contrato de piloto documentado. Funcionalidades reservadas a outros recortes permanecem descritas em cada Spec. Evidências em [checkpoint](../docs/memory/RESUME_POINT.md). Revisão independente pendente.

| Recorte | Spec | Estado |
| --- | --- | --- |
| Identidade e operadores | [IDN-001](users/SPEC.md) | VALIDATED |
| Matriz de acesso | [ACE-001](access-control/SPEC.md) | VALIDATED |
| Layout e identidade visual | [HOM-001](frontend/SPEC.md) | VALIDATED |
| Português e espanhol | [LOC-001](localization/SPEC.md) | VALIDATED |
| Catálogo por SKU | [CAT-001](products/SPEC.md) | VALIDATED |
| USD/PYG, câmbio, preços e custos | [CAM-001](products/CURRENCY.md) | VALIDATED |
| Estoque e histórico | [EST-001](inventory/SPEC.md) | VALIDATED |
| Clientes | [CLI-001](customers/SPEC.md) | VALIDATED |
| Fornecedores | [FOR-001](suppliers/SPEC.md) | VALIDATED |
| Venda administrativa | [VEN-001](sales/SPEC.md) | VALIDATED |
| Títulos, baixas e estornos | [FIN-001](finance/SPEC.md) | VALIDATED |
| Comissão percentual configurável | [COM-001](commissions/SPEC.md) | VALIDATED |
| Estoque, vendas e fluxo financeiro | [REL-001/002](reports/SPEC.md) | VALIDATED |
| Auditoria administrativa | [AUD-001](audit/SPEC.md) | VALIDATED |
| Dados da empresa e recibo simples | [VEN-002](sales/SPEC.md#ven-002--dados-da-empresa-e-recibo-simples-de-venda) | VALIDATED |
| Conta DEV e manutenção | [IDN-002](users/SPEC.md#idn-002--perfil-dev-para-manutenção) | VALIDATED |

A definição comercial é aplicada por configuração explícita do MASTER em Câmbio e Comissões. A futura operação com dados reais e VPS exige destino, TLS, privilégios definitivos de banco e backup operacional. O piloto utiliza uma empresa e dados fictícios.

## Evolução

Manter solicitação, Spec, impacto, autorização, implementação, testes e evidências nos documentos responsáveis. Novas regras preservam snapshots e registros existentes. Migrações aplicadas são imutáveis, com novo arquivo para cada evolução.
