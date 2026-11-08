# Docker local e preparação para VPS

## Preparação

Docker Desktop em modo Linux e Compose. A senha do PostgreSQL fica em .local/db_password, fora do Git e da imagem. Gere esse arquivo uma vez antes do primeiro uso.

PowerShell na raiz do projeto:

```powershell
New-Item -ItemType Directory .local -Force
if (!(Test-Path .local/db_password)) {
  $secretBytes = [byte[]]::new(32)
  [Security.Cryptography.RandomNumberGenerator]::Fill($secretBytes)
  [IO.File]::WriteAllText((Join-Path (Get-Location) '.local/db_password'), [Convert]::ToHexString($secretBytes))
}
docker compose up -d --build --wait
```

Em Linux, para uma instalação nova:

```sh
mkdir -p .local
chmod 700 .local
umask 077
test -f .local/db_password || openssl rand -hex 32 > .local/db_password
chmod 444 .local/db_password
docker compose up -d --build --wait
```

Conserve a senha já existente ao atualizar uma instalação. O banco mantém sua credencial inicial no volume. O arquivo precisa estar legível pelo UID 10001 da aplicação quando montado no container. Ajuste proprietário e grupo do arquivo conforme o ambiente Linux autorizado.

Acesse http://127.0.0.1:8765/. APP_PORT pode alterar a porta local. O PostgreSQL fica acessível apenas pela rede interna do Compose.

## Administração

```sh
docker compose ps
docker compose logs --tail=50 app migrate db
docker compose exec app python -m app.container_entrypoint python -m app.bootstrap_master nome-do-master
docker compose exec app python -m app.container_entrypoint python -m app.recover_master
docker compose down
docker compose up -d --wait
```

Os comandos administrativos leem a senha PostgreSQL do secret. A senha do MASTER é solicitada no terminal. A imagem executa a aplicação como UID 10001. Migrações precedem o servidor e bloqueiam sua inicialização se falharem. O histórico verifica checksum e serializa a aplicação por bloqueio PostgreSQL. Bancos existentes sem histórico exigem conferência antes de adoção.

## Backup e retorno

```sh
docker compose exec -T db pg_dump -U esther -d esther_beauty -Fc -f /tmp/esther.dump
docker compose cp db:/tmp/esther.dump .local/esther.dump
```

Proteja o arquivo conforme os dados armazenados. Restaure primeiro em banco separado e confira os registros. O volume postgres_data mantém o banco após parar ou recriar os containers. Para retorno da aplicação, use a imagem anterior com o volume preservado e confira compatibilidade das migrações.

## Verificações locais

```sh
docker compose exec -T app python -m pip check
docker compose run --rm migrate
docker compose exec -T app python -m app.container_entrypoint python -c "import os, unittest; os.environ['IDENTITY_TEST_DSN'] = 'host=db dbname=esther_beauty user=esther'; result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover('tests')); raise SystemExit(not result.wasSuccessful())"
```

Os testes PostgreSQL criam e removem esquemas aleatórios. Use ambiente de homologação.

## VPS

Use o complemento `compose.production.yaml` para homologar em Linux com a configuração de produção. Ele usa um projeto Compose separado do piloto. Use também um nome de projeto distinto para homologação com `-p`. O procedimento abaixo pressupõe um volume PostgreSQL novo. Para trazer dados existentes, restaure primeiro em homologação com os objetos pertencendo a `esther_migrate` e valide o histórico e a aplicação antes de trocar o destino.

Crie quatro senhas distintas no gerenciador de segredos e disponibilize-as em arquivos de uma linha no host. Use `.local/production/admin`, `.local/production/migrate`, `.local/production/app` e `.local/production/fx`. Restrinja o diretório ao responsável pelo deploy e confira a leitura pelos usuários dos respectivos containers. Cada serviço monta apenas seu arquivo. Digite as senhas do banco no prompt do psql. Provisione MASTER e DEV em terminal interativo com senhas próprias, distintas das credenciais de banco e da demonstração.

Configure `ESTHER_PROXY_IP` com o endereço único do proxy como visto pelo Uvicorn. Em Docker, confirme esse endereço a partir de uma requisição real. O proxy deve aceitar somente o domínio configurado, redirecionar HTTP para HTTPS e sobrescrever `X-Forwarded-Proto` e `X-Forwarded-For` com o esquema e o IP que ele próprio verificou. A aplicação permanece no loopback e o banco sem porta publicada.

Suba só o banco no primeiro provisionamento e abra o psql como administrador:

```sh
docker compose -f compose.yaml -f compose.production.yaml up -d --wait db
docker compose -f compose.yaml -f compose.production.yaml exec db psql -U esther -d esther_beauty -v ON_ERROR_STOP=1
```

```sql
CREATE ROLE esther_migrate LOGIN;
CREATE ROLE esther_app LOGIN;
CREATE ROLE esther_fx LOGIN;
\password esther_migrate
\password esther_app
\password esther_fx
REVOKE ALL ON DATABASE esther_beauty FROM PUBLIC;
GRANT CONNECT ON DATABASE esther_beauty TO esther_migrate, esther_app, esther_fx;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO esther_migrate;
GRANT USAGE ON SCHEMA public TO esther_app, esther_fx;
```

Use as senhas correspondentes aos arquivos montados. A migração aplica as permissões de execução na mesma transação e os serviços dependem da conclusão dela. Nos comandos administrativos desta página, inclua o complemento Compose para operar no ambiente correto.

### Verificação em duas etapas

Antes de subir a aplicação pela primeira vez, gere uma chave de 32 bytes para cifrar os segredos dos autenticadores. A aplicação lê 64 caracteres hexadecimais em `.local/production/mfa_key`. Gere apenas se o arquivo ainda não existir e garanta leitura pelo UID 10001 da aplicação. Guarde uma cópia protegida separada do backup do banco. A perda da chave exige recadastrar os autenticadores. Preserve a mesma chave ao atualizar ou restaurar a instalação.

```sh
umask 077
test -f .local/production/mfa_key || openssl rand -hex 32 > .local/production/mfa_key
```

Com a chave e as permissões do arquivo preparadas, execute `docker compose -f compose.yaml -f compose.production.yaml up -d --build --wait`.

Produção exige senha e código de aplicativo autenticador para DEV, MASTER e operadores. Após criar cada conta, emita o código de ativação em um terminal privado e interativo.

```sh
docker compose -f compose.yaml -f compose.production.yaml exec app python -m app.container_entrypoint python -m app.enroll_mfa nome-do-usuario --issue-activation
```

O código vence em 24 horas. Entregue-o à pessoa pelo canal interno autorizado, separado da senha inicial. No primeiro acesso, a pessoa digita a senha e o código de ativação, escaneia o QR Code no Google Authenticator e confirma com o código de seis dígitos. A tela oferece uma chave manual para quem está no mesmo dispositivo. O desafio vence em cinco minutos. Se a pessoa voltar à tela de login e começar outro desafio, deve escanear o novo QR Code. O cadastro confirmado consome a ativação.

Para cadastrar em terminal privado ou substituir um autenticador perdido, verifique primeiro a identidade da pessoa e execute o comando sem a opção de ativação.

```sh
docker compose -f compose.yaml -f compose.production.yaml exec app python -m app.container_entrypoint python -m app.enroll_mfa nome-do-usuario
```

No aplicativo autenticador, adicione uma conta com chave manual, baseada em tempo, de seis dígitos. Digite a chave exibida no terminal diretamente no dispositivo e confirme com o código gerado. Aguarde o próximo código para entrar. Não copie a chave para chat, e-mail ou registros. Sincronize o relógio da VPS e do dispositivo.

O comando substitui a chave, encerra sessões e registra o evento. Redefinir a senha preserva o segundo fator. Em homologação, utilize chaves e dispositivos de teste próprios.

Antes de publicar, confirme HTTPS e cookie `Secure` no navegador, IP do visitante no limite de login, rejeição de cabeçalhos forjados, ausência de portas públicas do banco e da aplicação, e execução dos fluxos com papéis restritos. Revise firewall e SSH, verifique dependências e imagens, configure backup externo protegido e restaure uma cópia. Registre domínio, versão, retenção, responsáveis e procedimento de retorno.

## Câmbio e histórico de migrações

O serviço fx_worker consulta a referência diária oficial do Banco Central do Paraguai a cada hora. Origem, data e estado aparecem em Câmbio. A política comercial inicia no modo automático oficial.

As migrações usam checksum de bytes e .gitattributes preserva os arquivos SQL entre Windows e Linux. Preserve esses arquivos após aplicação e crie um novo arquivo para evoluções posteriores.
