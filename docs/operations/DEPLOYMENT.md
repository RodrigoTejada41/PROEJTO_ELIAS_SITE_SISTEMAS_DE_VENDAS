# Implantação proposta

Separar desenvolvimento, homologação e produção. Fixar artefato e configuração por ambiente. Revisar segredos, migrações e backup, publicar após autorização, executar smoke test e monitorar erros, latência e banco. Registrar responsável, janela, versão anterior e condição de retorno. Provedor, CI, Docker e proxy dependem da decisão de infraestrutura.

## SEC-001 — Preparação da VPS

Em 08/11/2026, o usuário autorizou corrigir os bloqueios de segurança identificados na revisão estática. O Compose local compartilha a credencial de administração do banco e ignora os cabeçalhos do proxy. A implantação usará um complemento Compose com credenciais separadas para migração, aplicação e worker. O PostgreSQL permanece na rede interna. O proxy termina HTTPS, sobrescreve os cabeçalhos encaminhados e é identificado por um IP explícito.

Preservar o Compose de desenvolvimento e as migrações já aplicadas. Provisionar primeiro em banco limpo de homologação. Migrar dados existentes em restauração separada com os objetos pertencendo ao papel de migração. Para retorno, manter a imagem anterior e um backup restaurável, sem remover o volume.

Aceite antes de publicar: verificar cookie Secure, IP do visitante e rejeição de cabeçalhos forjados, execução dos fluxos com papéis restritos, impossibilidade de DDL pelos serviços, isolamento do banco, varredura de dependências e imagens e restauração de backup externo.
