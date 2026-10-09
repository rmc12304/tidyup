# Trabalho no Tidyup

Interface e documentação em português do Brasil. Python >=3.12, runtime sem dependências externas. Execute comandos na raiz do checkout.

## Comandos

- Testes obrigatórios: `python3 -m unittest discover -s tests -v`.
- Sintaxe: `python3 -m compileall -q tidyup`; `node --check tidyup/static/app.js` se Node estiver disponível.
- Início: `python3 -m tidyup --data-dir /diretorio/externo/dedicado`.
- Navegador opcional: `python3 -m tests.browser_smoke` (Playwright/Chromium).
- Benchmark sintético: `python3 -m tests.benchmark`.
- Pacote local/HTML: `python3 tools/build_local.py`; ZIP em `dist/`, sem dados operacionais.
- Abertura sem terminal Windows: `Abrir Tidyup.cmd` (requer Python >=3.12); encerrar pela interface.
- Smoke Win32 opcional: `TIDYUP_WINDOWS_FIXTURE_TESTS=1` + `python -m tests.windows_smoke` em Windows nativo. Só leitura/COM; não move/restaura.

## Organização

`core.py`: inventário, comparação, planos e execução. `filesystem.py`: validação de raízes e leitura ancorada. `native.py`: contrato de Lixeira, desabilitada. `storage.py`: SQLite transacional. `server.py`: API loopback/CSRF. `static/`: interface. `tests/`: fixtures temporárias. `docs/`: contratos, recuperação e cobertura.

`windows_recycle.py`: camada COM compartilhada. `WindowsTrash`: implementação do adaptador, ainda desabilitada por padrão. `WindowsFixtureTrash`: habilitado somente por injeção no runner `windows_flow_test.py`, restrito à raiz nova em TEMP. **Testar Fluxo Windows.cmd** é o opt-in explícito para esse teste. Não criar opção de ativação por variável de ambiente, diagnóstico ou relatório isolado; manter limpeza comum bloqueada até validação do fluxo/cenários nativos.

## Registros e condução proativa

O usuário pediu manutenção contínua dos registros e participação nas decisões. Antes de cada tarefa, consulte `docs/BACKLOG.md`, `docs/PROXIMOS_PASSOS.md` e `CHANGELOG.md`. Ao concluir uma mudança, descobrir um bloqueio, receber evidência de teste ou uma decisão, atualize os registros afetados na mesma tarefa. Use IDs estáveis do backlog, critérios de conclusão e estados honestos; diferencie execução nativa, simulação e proposta. Registre feitos no changelog, pendências no backlog e apenas a sequência priorizada/bloqueios/decisões nos próximos passos. Preserve o histórico de versões.

Conduza o trabalho autorizado proativamente; não exija que o usuário escolha detalhes rotineiros. Para decisões de produto/escopo/distribuição, apresente recomendação e consequências concretas e registre a escolha. Não trate silêncio como aprovação de publicação ou mudança de escopo. Ao responder, indique a próxima ação e só destaque decisões que precisam dele. Não prometa atualizações em segundo plano entre sessões. Relatórios privados nunca são incorporados aos registros: registre apenas conclusões sem caminhos pessoais.

## Limites obrigatórios

Não ler pastas pessoais sem autorização específica do escopo. Não mover arquivos pessoais durante desenvolvimento. Não habilitar Lixeira de produção sem teste nativo comprovado, reciclagem obrigatória e resultados por item. Política atual autorizada pelo usuário: revalidar identidade/hash de origem e referência imediatamente antes; bloquear mudanças detectadas, aceitando a pequena janela concorrente após liberar handles. Não prometer atomicidade nem preservação eterna da referência. Não usar exclusão permanente, shell com caminhos de entrada, fallback destrutivo ou esvaziamento. A referência nunca é movida. Cache nunca autoriza operação. Planos aceitam IDs, nunca caminhos do cliente. Bloqueios técnicos não admitem exceções.

Teste real de Lixeira explicitamente autorizado para fixture: duplo clique em `Testar Lixeira.cmd`, Windows nativo e Python >=3.12. Cria uma fixture nova em TEMP; nenhum caminho pessoal é recebido. Intenção/resultados fora do repo em LOCALAPPDATA/Tidyup/native-test-reports. Manter fixture/referência e relatório; não limpar por exclusão permanente. Não ativar produção automaticamente com um único teste aprovado. No Linux, registrar `not_executed`, nunca tratar mocks como prova nativa.

Não comitar caminhos pessoais, dados operacionais, logs ou segredos. Dados sempre fora do checkout. Preserve alterações existentes; inspecione `git status` antes/depois e os arquivos preparados para commit. Não publicar, fazer push/merge ou criar tags sem autorização. Mudanças de contrato exigem revisão e notas de compatibilidade; mantenha versão do esquema e changelog.

## Duas pessoas

Uma tarefa com escopo definido, uma branch por mudança, um responsável por árvore de trabalho. Revisão por PR e testes antes da integração. Desenvolvedores simultâneos devem usar ambientes/árvores separados; nunca dois agentes editando a mesma branch/árvore. Cada tarefa cloud já é isolada: use o checkout existente e só crie worktree se o usuário pedir. Não delegue edições simultâneas neste checkout. Pacotes/tags futuros só com autorização.
