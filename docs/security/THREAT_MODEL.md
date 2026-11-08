# Ameaças iniciais

| Fronteira | Ameaça | Controle e evidência esperada |
| --- | --- | --- |
| Navegador → aplicação | Sequestro de sessão, XSS, CSRF | HTTPS, cookies seguros quando aplicável, codificação de saída e teste de requisição forjada |
| Usuário → recurso | Escalada ou acesso por ID | Menor privilégio e teste cruzado por ator e empresa |
| Aplicação → banco | Injeção, duplicidade, corrida | Queries parametrizadas, constraints e testes transacionais |
| Relatórios → exportação | Vazamento e fórmulas injetadas | Escopo autorizado e teste de conteúdo hostil |
| Operações → logs/backups | Exposição de dados ou adulteração | Redação, retenção, acesso restrito e restauração testada |

DRAFT. Classificação de dados, fluxos externos e retenção dependem da modelagem.
