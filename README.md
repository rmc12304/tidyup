# Tidyup 0.3.0

**Estado do projeto:** versão em desenvolvimento, sem lançamento oficial. O envio inicial do código para a branch `main` do GitHub está autorizado e em preparação. A validação do fluxo 0.3.0 no Windows continua pendente.

Aplicativo local de revisão de arquivos, em português do Brasil, independente do PM Cockpit. Inventário real somente leitura, comparação SHA-256 por conteúdo, evidências lado a lado, seleção individual, revisão final e armazenamento local.

**Limite desta entrega:** o inventário foi validado no Linux. A limpeza de arquivos pessoais está **indisponível em todos os sistemas**, inclusive Windows. Um teste de fixture executado pelo usuário com Tidyup 0.2.1 e Python 3.14.8 confirmou reciclagem nativa, ausência da origem e hashes esperado/reciclado/referência iguais. Isso confirma a correção de metadados, mas não constitui aprovação do adaptador completo ou da restauração. Esta entrega ainda não atende ao aceite de limpeza operacional do prompt 1.0.0. Não há exclusão permanente ou fallback.

O acompanhamento do projeto fica no [backlog](docs/BACKLOG.md), nos [próximos passos](docs/PROXIMOS_PASSOS.md) e no [changelog](CHANGELOG.md). Esses registros são atualizados a cada trabalho e decisão no projeto.

Na 0.3.0, o adaptador está ligado ao executor em um runner limitado a fixtures. Para validar no Windows, extraia o pacote e abra **Testar Fluxo Windows.cmd**. Confira o [procedimento](docs/teste-fluxo-windows.md). O resultado nativo desse fluxo ainda está pendente; o aplicativo normal permanece bloqueado.

## Abrir com duplo clique no Windows

1. Baixe `dist/tidyup-local.zip` e **extraia o pacote inteiro** em uma pasta local.
2. Com **Python 3.12 ou mais recente** instalado de python.org (launcher ou PATH habilitado), dê duplo clique em **Abrir Tidyup.cmd**. Se `.pyw` estiver associado ao Python, também pode abrir **Abrir Tidyup.pyw**.
3. O inicializador inicia o serviço em segundo plano e abre o HTML no navegador padrão. Não é necessário digitar comandos. Outro duplo clique reabre a mesma instância.
4. Use **Encerrar aplicativo** na interface para parar o serviço. Fechar só a aba mantém o serviço disponível. Dados Windows ficam em `%LOCALAPPDATA%/Tidyup`, fora do pacote, ou em `DATA_DIR` se configurado.

**Tidyup.html** é autocontido (CSS/JavaScript embutidos) e abre por duplo clique para visualizar a interface. Aberto via `file://`, explica como iniciar o componente local e bloqueia ações de disco. Navegadores não podem iniciar Python nem acessar a Lixeira ao abrir um HTML isolado. Para operar, use o inicializador. Não foram instalados protocolos ou alterações de registro.

Inicialização/reabertura/encerramento foram testados no Linux; `.cmd`, Pythonw e APIs Win32 precisam de validação Windows. Não tratar como integração de Lixeira concluída.

## Instalar e iniciar

Para testar a Lixeira no Windows sem terminal, use **Testar Lixeira.cmd** do pacote. Cria somente um arquivo sintético e sua referência, revalida hashes, solicita reciclagem via IFileOperation e registra resultados em LOCALAPPDATA. **A fixture básica da 0.2.1 passou no Windows do usuário; aqui só há Linux.** Veja [procedimento e critérios](docs/teste-lixeira.md). Não habilita a limpeza de arquivos pessoais automaticamente.

Requer Python 3.12 ou mais recente. Não há dependências externas de runtime, banco externo, Node obrigatório, telemetria nem uploads. O lockfile de runtime é `requirements.lock` (vazio intencionalmente).

No diretório do projeto:

```sh
python3 --version
python3 -m unittest discover -s tests -v
python3 -m tidyup --data-dir /caminho/fora/do/repo/tidyup-dados
```

Substitua o diretório de dados por um caminho absoluto dedicado fora do checkout e de todas as raízes examinadas. Sem `--data-dir`, usa `DATA_DIR`, ou `~/.local/share/tidyup`. O diretório é criado se necessário. O serviço escuta exclusivamente `127.0.0.1`, porta 8765 por padrão (`--port` permite mudar). Abra o endereço local informado pelo terminal **na mesma máquina**. Um serviço na nuvem não acessa a pasta Downloads do seu computador: para revisar seus arquivos, execute o projeto localmente em um sistema suportado. Não exponha a porta na rede.

Encerre com **Ctrl+C**. Cancelar na interface interrompe novas leituras/operações; não desfaz resultados anteriores. Ao retomar um inventário, a varredura recomeça e revalida as identidades; hashes já concluídos podem ser reaproveitados. Depois de reiniciar, não se presume que um inventário em andamento terminou.

## Usar

1. Informe o caminho absoluto da origem e uma ou mais referências, uma por linha. Nenhum caminho Downloads é presumido. Não há busca automática de discos nem seletor nativo de pastas nesta versão.
2. Marque explicitamente a opção de subpastas se quiser recursão em todas as raízes. Clique em **Validar raízes** e confira os caminhos apresentados.
3. Inicie o inventário somente leitura. Referências são sempre somente leitura. Progresso mostra etapa, itens e bytes efetivamente lidos (cache não aumenta esses bytes).
4. Examine os estados: cópia verificada, mesmo nome sem prova, nenhuma cópia encontrada no escopo, pendência ou bloqueio. Expanda os detalhes para consultar o SHA-256 completo, identidade e origem do hash. O pré-filtro de tamanho evita leituras desnecessárias.
5. Selecione arquivos individualmente. Sem cópia, o checkbox declara um **descarte excepcional**; bloqueios técnicos não podem ser contornados. Nada começa selecionado. Seleção continua entre páginas de 50 itens.
6. Revise a lista exata, seus bytes e a referência preservada. A ação **Mover N arquivos para a Lixeira** permanece desabilitada pela falta de adaptador nativo. Não execute uma limpeza manual como demonstração.

Bytes selecionados não equivalem a espaço imediatamente liberado. Lixeira ainda ocupa armazenamento; remoções em pastas sincronizadas podem propagar para a nuvem. Conteúdo offline/sob demanda e reparse points são bloqueados; o aplicativo não pede hidratação. Leituras comuns podem atualizar a data de acesso do sistema de arquivos, mas o aplicativo não escreve na origem ou nas referências.

## Validação e limitações

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q tidyup
python3 -m tests.benchmark
# Opcional, apenas para desenvolvimento, com Playwright e Chromium instalados:
python3 -m tests.browser_smoke
```

Testes usam exclusivamente diretórios temporários e arquivos sintéticos. O teste de navegador usa as ferramentas presentes no ambiente; `requirements-browser.lock` fixa suas versões opcionais. CI executa o núcleo e a API no Linux. Veja [resultados e cobertura](docs/testes.md).

Além do teste básico relatado pelo usuário, não houve validação Windows completa, macOS, restauração do SO, junctions reais, arquivos de nuvem reais ou varredura de seus 12 GB. Não se anuncia suporte operacional dessas funções. Leitura Windows experimental usa handles sem compartilhamento DELETE (arquivo também sem WRITE), verifica atributos/reparse tags e abre caminhos estendidos. **Verificar compatibilidade com a Lixeira** só cria COM e configura flags; nunca agenda exclusão. Hard links, links simbólicos, reparse points (inclusive CLOUD) e arquivos especiais são bloqueados conservadoramente.

O próximo passo para limpeza operacional é implementar e validar o adaptador Windows descrito em [integração nativa](docs/nativo.md), em uma máquina Windows e somente com fixtures. Até lá, use esta versão para inventário/revisão no Linux.

## Dados, recuperação e colaboração

Configuração, backup de configuração, inventário atual, cache de hashes, planos e auditoria ficam no `DATA_DIR/state.sqlite3`, nunca no repositório. Eles contêm caminhos pessoais: mantenha acesso restrito à sua conta, sem sincronização/upload automático. No POSIX, novos diretórios usam 0700 e banco 0600; permissões de diretórios já existentes devem ser conferidas pelo operador. Não há expiração automática nesta versão. [Retenção, backup e recuperação](docs/recuperacao.md) explicam como mudar o diretório, lidar com resultado incerto e fazer rollback.

Consulte [arquitetura](docs/arquitetura.md), [contratos](docs/contratos.md), [integração futura](docs/integracao.md), [AGENTS.md](AGENTS.md) e [CHANGELOG.md](CHANGELOG.md). Nenhum dado operacional deve ser preparado para commit. Publicar versões, push ou merge exigem autorização.
