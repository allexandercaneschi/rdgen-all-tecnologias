# RDGen, a RustDesk client generator to use with your self-hosted RustDesk server

The client generator is currently hosted [here](https://rdgen.crayoneater.org).
If you would like to host the generator yourself, see [here](setup.md)

## Features

- Embed server and key into client
- Custom app name
- Custom icon/logo
- Set default settings for the client
- Support for rustdesk advanced settings (https://rustdesk.com/docs/en/self-host/client-configuration/advanced-settings/)

## Generate RustDesk clients from command line instead of using a web browser

Save your configuration from the rdgen web interface, or generate your own, then use that json file with [@AlekseyLapunov's rdgen-cli](https://github.com/AlekseyLapunov/rdgen-cli) to build from the command line on Windows, Linux, or MacOS like this: `python rdgen-cli -f my_config.json --set-version 1.4.5 --set-platform windows -s https://rdgen.crayoneater.org`

## Builds geradas e links "latest" (fork ALL Tecnologias)

Todas as builds ficam guardadas em `exe/<uuid>/` (monte esse diretório como volume para não perder nada ao atualizar o container).

- **`/builds`**: painel protegido por usuário e senha que lista todas as builds, com download de cada arquivo e botão para excluir builds antigas. Defina `BUILDS_PASSWORD` (e opcionalmente `BUILDS_USER`, padrão `admin`); sem senha o painel fica desativado.
- **`/latest/<arquivo>`**: link público e fixo que sempre entrega a versão mais recente daquele arquivo, para usar no site. Ex.: `/latest/ALLRemote.exe`, `/latest/ALLRemote.msi`, `/latest/ALLRemote-aarch64.apk`.
- **Atalhos por tipo**: `/latest/exe`, `/latest/msi`, `/latest/apk` (aarch64), `/latest/apk-armv7`, `/latest/apk-x86_64`, `/latest/dmg`, `/latest/dmg-intel`, `/latest/deb`, `/latest/rpm`, `/latest/appimage`. Entregam o arquivo mais recente daquele tipo, de qualquer build; use só se o servidor gera um único nome de app.
- Para desativar os links públicos, defina `LATEST_ENABLED=false`.
- Excluir uma build no painel faz os links `/latest` voltarem a apontar para a build anterior.

## Notes

- Icons should be square (256x256 recommended)
- Avoid special characters or non-English characters in app name and file name
- Build time is currently 30 - 45 minutes

