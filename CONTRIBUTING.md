# Como contribuir

Obrigado por querer ajudar! Este é um projeto pessoal, feito por alguém que não
é programador, e toda sugestão é bem-vinda — inclusive as que não envolvem
código.

## Antes de abrir uma issue

- Procure se já existe uma issue parecida.
- Use os templates de **bug** ou **sugestão**.
- Se for um problema, inclua:
  - modelo do fone (ex.: FreeBuds Pro 5);
  - firmware exibido no app oficial, se souber;
  - versão do Windows;
  - o que você fez, o que esperava e o que aconteceu;
  - a mensagem de erro ou trecho do log.
- **Não publique endereço Bluetooth completo, serial, capturas HCI ou nomes de
  dispositivos.** Se precisar mostrar um log, redija esses dados.

## Sugestões

Não precisa saber programar para sugerir. Ideias de uso, textos, acessibilidade,
instalação mais fácil e melhorias de layout são muito úteis. Se você tiver o fone
e puder testar em outro modelo/firmware, isso ajuda ainda mais.

## Pull requests

- Descreva o que mudou e por quê.
- Diga em qual modelo/firmware/Windows você testou. Se não testou em hardware,
  deixe isso claro.
- Mantenha o escopo pequeno e explique decisões que afetam o protocolo.
- Rode as verificações localmente:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check src tests
.\.venv\Scripts\python.exe -m compileall -q src tests
```

- Não inclua capturas, seriais, MACs ou arquivos de configuração pessoais.
- Não adicione imagens, ícones ou textos de terceiros sem permissão. Se o material
  tiver direitos autorais, ele não pode ser coberto pela licença MIT.
- Não implemente atualização de firmware nem contorno de pareamento/segurança.

## Conduta

Seja respeitoso. Críticas técnicas são bem-vindas; ataques pessoais, discriminação
e exposição de dados pessoais não são. Veja
[`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

## Tempo de resposta

Este é um projeto de aprendizado, sem suporte oficial ou prazo. Eu respondo quando
consigo. Se demorar, não é falta de interesse.
