# Changelog

## 0.3.0 — em desenvolvimento, sem lançamento oficial

### 2026-10-08 — preparação do envio inicial ao GitHub

- Usuário autorizou primeiro commit e push para `main` em `rmc12304/tidyup`. Revisão dos arquivos e verificações finais antes do envio.
- Estado do código separado do estado de lançamento: enviar ao GitHub não significa criar release ou habilitar limpeza operacional.
- `.gitignore` ampliado para impedir inclusão acidental de bancos, relatórios nativos, metadados de instância e arquivos de ambiente. Pacotes gerados continuam fora do Git; podem ser reconstruídos com `python3 tools/build_local.py`.

### Implementação

- Camada COM de reciclagem extraída para `windows_recycle.py` e compartilhada entre teste básico e adaptador Windows. Mantidas flags obrigatórias de reciclagem, callbacks e comprovação por hash.
- Implementado o caminho de execução do adaptador: raiz/identidade/hash revalidados antes e no callback, cancelamento antes da movimentação, evidências por item e resultado incerto após exceção na camada nativa. Adaptador padrão continua desabilitado até ampliar validação Windows.
- Executor transmite identidades das raízes e sinal de cancelamento ao adaptador; preserva diagnósticos de resultado incerto e não aceita falha segura quando a origem desapareceu.
- Adicionado **Testar Fluxo Windows.cmd**: Engine real, duas seleções incluindo Unicode, referências e item não selecionado preservados, bloqueio de origem/referência alteradas, repetição de plano e reabertura do banco. Limitado a fixtures novas em TEMP; relatório e banco fora do pacote.
- Validação na nuvem é sintética; teste nativo da 0.3.0, interface Windows e restauração permanecem pendentes. Esquema 1 preservado, sem migração. Reiniciar o processo antes de trocar arquivos do pacote; rollback para 0.2.1 com processo encerrado é compatível com o esquema, sem restaurar itens movimentados.

## Ainda não lançado

### 2026-10-07 — registros e validação

- Criados backlog com prioridades e critérios de conclusão e próximos passos com dependências, bloqueios e decisões. AGENTS.md orienta sua manutenção proativa em cada tarefa.
- Registrado o relatório Windows fornecido pelo usuário: Tidyup 0.2.1, Python 3.14.8, resultado `passed`, pré-validação aprovada, operação nativa sem cancelamento, origem ausente e hashes esperado/reciclado/referência iguais. Confirma a correção de metadados e a reciclagem da fixture. Relatório e caminhos privados não foram incorporados ao repositório.
- Documentação atualizada para retirar a repetição do teste básico dos bloqueios pendentes. Adaptador operacional, cobertura Windows completa e restauração continuam pendentes; limpeza normal permanece desabilitada.

## 0.2.1 — não publicada

- Correção da comparação stat/lstat versus fstat no Windows: nascimento/criação é normalizado apenas na comparação entre caminho e descritor. ChangeTime bruto continua verificado entre as leituras do descritor.
- Quatro testes de regressão: diferença legítima após reciclagem, substituição real, mudança durante leitura e comportamento POSIX preservado.
- Relatórios agora identificam versão do app/Python e incluem assinaturas diagnósticas se a validação falhar; dados operacionais continuam fora do repo.
- Pacote com nome versionado para distinguir a correção. Sem migração de esquema ou ativação automática da limpeza.

## Atualização não publicada após 0.2.0

- Política autorizada: revalidar origem/referência imediatamente antes da operação, aceitando janela concorrente residual.
- Teste real opt-in por duplo clique, limitado a fixture própria, com IFileOperation, callbacks, HRESULT e verificação de conteúdo reciclado.
- Runner registra `not_executed` no Linux; nenhuma aprovação Windows alegada. Produção continua bloqueada até validação nativa.

## 0.2.0 — não publicada

- Inicializador Windows por duplo clique: serviço em segundo plano e navegador automático; reabertura da mesma instância.
- Encerramento pela interface, protegido por Origin/CSRF; identificador local impede reuso de serviço estranho.
- HTML autocontido e pacote ZIP sem dados operacionais.
- Leitura Windows experimental por handles, caminhos estendidos e bloqueio de reparse/offline/rede.
- Diagnóstico COM IFileOperation/flags sem enfileirar exclusões. Lixeira continua bloqueada: proteção de localização versus compartilhamento DELETE não resolvida/validada.
- Esquema 1 preservado, sem migração. APIs adicionadas; rollback para 0.1.0 com backup e processo encerrado é compatível com o banco. Não restaura arquivos.

## 0.1.0 — não publicada

- Inventário real POSIX em raízes explícitas, recursão opcional e leitura ancorada.
- Pré-filtro por tamanho e SHA-256 completo em streaming; cache por identidade e metadados.
- Painel de revisão responsivo, estados de evidência, seleção individual, exceções e planos imutáveis.
- API loopback com Host/Origin/CSRF, SQLite com registros duráveis e bloqueio de operações incertas.
- Lixeira desabilitada em todas as plataformas até validação nativa; testes de execução são sintéticos.
- Esquema de dados 1, documentação, testes portáveis e CI Linux.

A versão do aplicativo é independente do prompt de requisitos 1.0.0. Nenhuma migração de esquema foi necessária nesta versão inicial.
