# Implantação proposta

Separar desenvolvimento, homologação e produção. Fixar artefato e configuração por ambiente. Revisar segredos, migrações e backup, publicar após autorização, executar smoke test e monitorar erros, latência e banco. Registrar responsável, janela, versão anterior e condição de retorno. Provedor, CI, Docker e proxy dependem da decisão de infraestrutura.

## SEC-001 — Preparação da VPS

Em 08/11/2026, o usuário autorizou corrigir os bloqueios de segurança identificados na revisão estática. O Compose local compartilha a credencial de administração do banco e ignora os cabeçalhos do proxy. A implantação usará um complemento Compose com credenciais separadas para migração, aplicação e worker. O PostgreSQL permanece na rede interna. O proxy termina HTTPS, sobrescreve os cabeçalhos encaminhados e é identificado por um IP explícito.

Preservar o Compose de desenvolvimento e as migrações já aplicadas. Provisionar primeiro em banco limpo de homologação. Migrar dados existentes em restauração separada com os objetos pertencendo ao papel de migração. Para retorno, manter a imagem anterior e um backup restaurável, sem remover o volume.

Aceite antes de publicar: verificar cookie Secure, IP do visitante e rejeição de cabeçalhos forjados, execução dos fluxos com papéis restritos, impossibilidade de DDL pelos serviços, isolamento do banco, varredura de dependências e imagens e restauração de backup externo.

## Implantação em /Sistema

Destino autorizado: VPS Esther Beauty 777 em `https://estherbeauty777.com/Sistema/`. A raiz fica reservada ao site institucional. O proxy existente retira o prefixo antes de encaminhar ao Compose. A aplicação inclui o prefixo em links, formulários, estáticos e redirecionamentos e restringe os cookies ao caminho do sistema.

Usar banco e volume novos com 19 migrações e apenas MASTER e DEV. Manter 2FA obrigatório, credenciais separadas e HTTPS. Validar a rota, a raiz, os estáticos, os cookies, o login e a ausência de dados de demonstração. Para retornar, desabilitar o proxy do sistema e preservar o volume.
