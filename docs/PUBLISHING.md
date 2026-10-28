# Publicando no GitHub

Este guia é para o autor do projeto. O código já está preparado; falta criar o
repositório no GitHub e enviar os arquivos. **Se o Git não estiver instalado**,
o caminho mais fácil é o GitHub Desktop.

## Antes de publicar

Confira estes pontos:

- [ ] A pasta `referenciasvisuais/` **não** deve ser enviada. Ela contém capturas
      pessoais com nomes de dispositivos e fica fora do Git pelo `.gitignore`.
- [ ] `.venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `settings.json`,
      `captures/` e `tmp_*` também estão ignorados.
- [ ] As imagens em `docs/ui/` usam dados sintéticos e não mostram MAC, serial ou
      nomes de pessoas.
- [ ] O `README.md`, o `CHECKPOINT.md` e os docs não têm endereço Bluetooth
      completo, serial ou caminho pessoal.
- [ ] Você leu o [`NOTICE.md`](../NOTICE.md) sobre a foto e os ícones de terceiros.

## Opção recomendada: GitHub Desktop

1. Instale o **GitHub Desktop** (https://desktop.github.com/) e entre na sua
   conta.
2. No menu **File**, escolha **Add Local Repository...** e selecione a pasta do
   projeto (`<PASTA_DO_PROJETO>`).
3. Se ele avisar que a pasta ainda não é um repositório Git, aceite criar um
   repositório nela. O GitHub Desktop inicializa o Git sem apagar os arquivos.
4. Abra a aba **Changes**. Confirme que **não** aparecem `.venv`,
   `referenciasvisuais`, `__pycache__`, `settings.json`, `tmp_*` ou capturas.
   Se aparecer algum, pare e confira o `.gitignore`.
5. Em **Summary**, escreva algo como `Versão inicial do FreeBuds Client` e clique
   em **Commit to main**.
6. Clique em **Publish repository**:
   - **Name:** `freebuds-client` (ou `freebuds-pc-client` se preferir evitar
     confusão com outros projetos);
   - **Description:** use a sugestão abaixo;
   - desmarque **Keep this code private** para o repositório ficar público;
   - publique.
7. Depois de publicar, no GitHub:
   - **Settings → General:** adicione a descrição e os tópicos;
   - **Features:** mantenha **Issues** ligado; **Discussions** é opcional;
   - confira se o GitHub detectou a licença MIT;
   - **Actions:** permita os workflows se ele pedir. O CI roda a cada push.

### Descrição sugerida do repositório

> Cliente desktop não oficial (Windows) para HUAWEI FreeBuds — bateria, ANC,
> áudio, gestos e diagnóstico via SPP/RFCOMM. Projeto pessoal de aprendizado,
> aberto a sugestões.

### Tópicos sugeridos

`huawei`, `freebuds`, `bluetooth`, `rfcomm`, `spp`, `windows`, `python`,
`pyside6`, `harmonyos`, `desktop-app`.

## Opção alternativa: Git no terminal

1. Instale o **Git para Windows** (https://git-scm.com/download/win) ou use:
   ```powershell
   winget install --id Git.Git -e
   ```
2. Abra o PowerShell na pasta do projeto e rode:
   ```powershell
   git init
   git add .
   git status
   ```
3. Confira a lista do `git status`. **Não** devem aparecer `.venv`,
   `referenciasvisuais`, `__pycache__`, `settings.json`, `tmp_*` ou capturas.
4. Crie o commit e envie:
   ```powershell
   git commit -m "Versão inicial do FreeBuds Client"
   git branch -M main
   git remote add origin https://github.com/SEU_USUARIO/freebuds-client.git
   git push -u origin main
   ```
   Troque `SEU_USUARIO` pelo seu usuário do GitHub.

## Depois de publicado

- Atualizações: edite os arquivos, faça commit e `Push origin` (GitHub Desktop)
  ou `git push` (terminal).
- Se adicionar capturas de tela, use dados sintéticos ou redija nomes, MACs e
  seriais antes de commitar.
- Não crie uma release com instalador enquanto não existir um `.exe` testado.
  Por enquanto o projeto é distribuído como código-fonte.
- Se alguém pedir a remoção de uma imagem ou ícone de terceiros, atenda e
  substitua o material. Veja o [`NOTICE.md`](../NOTICE.md).
- Se quiser um instalador `.exe`, abra uma issue de sugestão; isso ainda não está
  implementado.

## Se algo der errado

- **O GitHub Desktop mostra arquivos demais:** verifique se o `.gitignore` está
  na raiz e se a pasta escolhida é a correta.
- **Push rejeitado por arquivo grande:** confirme que `.venv/` e
  `referenciasvisuais/` não foram adicionados por engano. As imagens de `docs/ui/`
  são pequenas e podem ir.
- **CI falhou:** abra a aba Actions, veja o passo que falhou e rode localmente
  `python -m pytest`, `python -m ruff check src tests` e
  `python -m compileall -q src tests`.
- **Dados pessoais foram publicados por engano:** apagar o arquivo no commit mais
  recente não remove o conteúdo do histórico. Torne o repositório privado,
  remova o arquivo e limpe o histórico (ou apague o repositório e publique de
  novo). Se possível, faça isso antes de divulgar o link.
