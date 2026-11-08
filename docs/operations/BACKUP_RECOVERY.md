# Backup e recuperação

Definir RPO, RTO, frequência, retenção, destino criptografado, responsáveis e permissões antes de produção. Incluir banco e ativos necessários. Testar restauração isolada, conciliar estoque e lançamentos e documentar o tempo observado. Confirmar cópia íntegra antes de migração crítica.

## Proposta para o piloto

Agendar uma execução na VPS para gerar backup lógico do PostgreSQL com pg_dump e copiar os ativos necessários, quando existirem. Criptografar antes do envio para armazenamento independente da BattleHost. Manter credenciais fora do código, com acesso mínimo e chave de recuperação sob custódia separada. Registrar data, tamanho, resultado de envio e falhas sem segredos. Alertar se a execução falhar ou se nenhuma cópia válida chegar no intervalo esperado.

Frequência diária é candidata se o cliente aceitar até 24 horas de perda de dados. Definir RPO, RTO, retenção e destino antes de habilitar dados reais. Validar restauração em ambiente separado, medir duração e conferir usuários, estoque e financeiro. Testar também recuperação com a VPS original indisponível.
