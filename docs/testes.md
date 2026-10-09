# Validação desta entrega

Executado no ambiente Linux x86_64, CPython 3.12.14; JavaScript verificado com Node 24.19.0. Foram usados apenas arquivos sintéticos em `TemporaryDirectory`. Nenhuma pasta pessoal foi inventariada ou limpa.

## Resultados

- **60 testes de núcleo/API/inicializador/contratos passaram no Linux**, sem skipped ou expected-failure. Comando: `python3 -m unittest discover -s tests -v`. Incluem abertura/reabertura, encerramento, isolamento do pacote, contratos Windows com simulações, classificação sem prova nativa e regressão da diferença stat/fstat no Windows. A 0.3.0 acrescenta simulações do adaptador e do runner: provas por hash, mudança de referência no callback, exceção após movimentação, hash reciclado errado, escopo, cancelamento, identidade de raiz, lote, seleção, bloqueios pós-plano e reabertura/idempotência.
- **Teste de navegador passou** com Chromium do sistema e Playwright 1.62.0, 107 origens sintéticas, viewport 390×844 e 1280×900. Validou início real pela interface, comparação, nada selecionado inicialmente, seleção por teclado, seleção persistente entre páginas, revisão exata, Escape no diálogo, ação de Lixeira bloqueada, nomes HTML renderizados como texto, ausência de erros JavaScript e de overflow horizontal. Comando: `python3 -m tests.browser_smoke`.
- Compilação Python e `node --check tidyup/static/app.js` passaram. Não há build/transpilação do frontend.
- Abertura direta `file://` do HTML no Chromium deste ambiente foi **bloqueada pela política administrativa do navegador**. Não foi alterada a política. A renderização e o ramo offline foram exercitados em memória com protocolo simulado: controles de disco desativados e nenhuma requisição de rede. Isso não prova abertura por duplo clique neste navegador nem em Windows. O botão de diagnóstico e o encerramento pelo HTML servido também foram exercitados.
- Benchmark sintético: **142.606.336 bytes lidos (136 MiB), dois arquivos, 0,1012 s**, concorrência de hash 1. Linux 6.18.44 x86_64/glibc 2.41, Python 3.12.14. Cache do aplicativo frio; cache do SO quente pela criação das fixtures. Não é medição de Downloads reais, nuvem ou disco frio e não permite prometer duração para 12 GB. Reproduzir: `python3 -m tests.benchmark`.

## Cobertura e limites

| Caso | Evidência |
|---|---|
| Mesmo nome/conteúdo distinto; nomes distintos/conteúdo igual; vazios | Testes reais de arquivos temporários e SHA-256 completo |
| Unicode, >260 caracteres, arquivo de 8 MiB | Inventário/hash POSIX e recursão explícita; não prova Windows |
| Sem mutações de origem/referência | Conteúdo e assinatura antes/depois; leitura pode alterar atime do SO |
| Alteração/remoção/substituição após inventário/plano | Revalidação rejeita plano ou bloqueia execução sintética |
| Mudança durante hashing; ancestral trocado por symlink | Hash bloqueado; abertura ancorada rejeita escape |
| Symlink/hard link | Fixtures reais POSIX bloqueadas |
| Reparse desconhecido/offline; permissão negada | Simulações de atributos/exceções, sem Windows/nuven reais |
| Sem candidato/exceção individual/referência selecionada | Política real do núcleo; exceções não desbloqueiam adaptação nativa |
| Lote não remove todas as cópias | Só referências externas podem justificar origens; referência preservada na execução sintética |
| Repetição, reinício/intenção incerta, ausência sem prova | Executor com adaptador sintético; bloqueio durável de identidade/localização |
| Falha parcial, cancelamento e mudança na fase nativa | Adaptador sintético; não comprova locking ou resultado nativo |
| Recuperação/hash | Restauração sintética por rename reversível; **não é restauração pela Lixeira do SO** |
| Host, Origin, CSRF, caminhos arbitrários | Requisições HTTP reais contra serviço loopback |
| Navegação/foco/lista grande/móvel | Automação Chromium; auditoria manual de acessibilidade com leitor de tela não executada |
| Contraste | Paleta de texto clara sobre fundo escuro inspecionada visualmente; auditoria WCAG automatizada não executada |

Não executados neste ambiente Linux: IFileOperation e reciclagem/restauração real. A reciclagem básica foi comprovada no Windows do usuário, conforme registro abaixo. Permanecem sem validação completa: restauração nativa, volumes de rede, junctions Windows reais, identificação de tags CLOUD reais, hidratação real/falha de provedor, garantias de concorrência nativa, long paths na movimentação Windows, macOS, arquivos pessoais/12 GB e recuperação de uma versão publicada em novo ambiente cloud. São bloqueadores de **movimentação operacional**, não resultados aprovados por mock.

`tests/windows_smoke.py` foi acrescentado como suíte opt-in de **leitura/COM**, ainda não executada por falta de Windows. Não recicla arquivos nem testa restauração. A futura suíte operacional de Lixeira deve ser isolada e explicitamente habilitada, com diretórios temporários e conferência do hash ao restaurar. Nunca executar contra raízes de uso pessoal.

O runner **Testar Lixeira.cmd** foi acrescentado para uma operação real de reciclagem de fixture em Windows, opt-in por duplo clique. Seu resultado aqui foi **not_executed**, não aprovado: não há Windows disponível. Contratos de callback/flags/classificação foram exercitados sinteticamente; restauração nativa continua não executada; a reciclagem básica foi executada no Windows do usuário, conforme registro abaixo. Consulte [procedimento](teste-lixeira.md).

O primeiro relatório Windows fornecido pelo usuário terminou `uncertain` devido à comparação de metadados antes do hash reciclado. O segundo relatório, com Tidyup 0.2.1 e Python 3.14.8, confirmou `passed`: pré-validação aprovada, PerformOperations sem erro, sem cancelamento, PostDeleteItem com sucesso/item reciclado, origem ausente e hashes esperado/reciclado/referência iguais. Isso confirma a reciclagem básica e a correção de metadados em Windows nativo. Não prova restauração ou adaptação operacional completa. Nenhum relatório/caminho privado foi copiado para o repositório.

Na 0.3.0, [Testar Fluxo Windows.cmd](teste-fluxo-windows.md) liga o adaptador ao Engine com fixtures próprias. Sua lógica passou em simulação POSIX; a execução nativa Windows permanece pendente. Não valida interface ou restauração.
