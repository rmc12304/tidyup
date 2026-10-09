# Integração nativa: bloqueador conhecido

## Política atual e teste nativo

O usuário substituiu a exigência de proteção contínua pela revalidação imediata de identidade/hash de origem e referência, aceitando a janela depois de liberar handles. O conflito de compartilhamento DELETE analisado abaixo não é mais requisito para impedir o avanço. O adaptador 0.3.0 está implementado e ligado ao Engine no runner de fixtures. O bloqueio atual é validar esse fluxo e ampliar a cobertura nativa Windows; a fixture básica da 0.2.1 já passou.

`windows_recycle_test.py` implementa o envio real por IFileOperation **somente para uma fixture criada pelo teste**. `Testar Lixeira.cmd` é o opt-in por duplo clique. Há callback PreDeleteItem com hashes frescos, PostDeleteItem por item, confirmação de reciclagem e hash do item reciclado. Consulte [teste real](teste-lixeira.md). No Linux foi registrado `not_executed`. No Windows do usuário, o relatório da 0.2.1 confirmou `passed`, inclusive o hash reciclado e a referência intacta. Essa prova básica não valida o fluxo operacional completo; o adaptador normal permanece desabilitado. Veja o [backlog](BACKLOG.md) e os [próximos passos](PROXIMOS_PASSOS.md).

`UnavailableTrash` bloqueia Linux/macOS e `WindowsTrash` também bloqueia movimentação Windows. Não há emulação de Lixeira. `windows.py` implementa leitura experimental por handles e diagnóstico COM, **não reciclagem operacional**. Não basta trocar `supported` para verdadeiro. A 0.3.0 compartilha COM em `windows_recycle.py` e usa `WindowsFixtureTrash` com escopo adicional limitado ao runner. [Testar Fluxo Windows.cmd](teste-fluxo-windows.md) exercita o Engine real, sem habilitar limpeza comum.

## Resultado da investigação 0.2.0

A fonte oficial de [CreateFileW](https://github.com/MicrosoftDocs/sdk-api/blob/docs/sdk-api-src/content/fileapi/nf-fileapi-createfilew.md) foi consultada: sem `FILE_SHARE_DELETE`, nenhum processo pode abrir o arquivo com acesso DELETE; acesso de exclusão inclui rename. Esse bloqueio protege conteúdo/localização na leitura, mas impede o Shell de reciclar enquanto o handle está protegido. Compartilhar DELETE ou fechar o handle antes de IFileOperation reabre a troca do caminho. Não foi estabelecida uma ponte atômica entre o handle validado e a operação do Shell. É um bloqueador de garantia, além da ausência de Windows para execução; não se resolve apenas liberando o bloqueio.

Leitura experimental: CreateFileW com OPEN_REPARSE_POINT/OPEN_NO_RECALL, FileAttributeTagInfo, rejeição de reparse/offline/sob demanda e volumes não locais. Ancestrais negam DELETE; arquivo nega WRITE/DELETE. Assinaturas são comparadas antes/depois e SHA-256 é streaming. Caminhos usam prefixo estendido. Não foi executada em Win32 aqui.

`probe_ifileoperation` instancia COM STA e configura RECYCLEONDELETE/EARLYFAILURE/NOERRORUI/NORECURSION; libera COM. Não chama DeleteItem ou PerformOperations. `available` só indica disponibilidade da API/flags; `operational` permanece false. A interface não transforma diagnóstico em autorização para limpar.

Suíte opt-in Windows: definir `TIDYUP_WINDOWS_FIXTURE_TESTS=1` e executar `python -m tests.windows_smoke` em Windows nativo. Cria fixtures Unicode e >260 caracteres, compara hash e verifica bloqueio de rename. **Não executa nem testa reciclagem/restauração.** A suíte completa abaixo continua pendente.

## Requisitos para um adaptador Windows

1. Provar que um destino não reciclável falha sem exclusão permanente. A documentação consultada descreve `FOFX_RECYCLEONDELETE (0x00080000)`, introduzida no Windows 8, como enviar para a Lixeira em vez de excluir permanentemente. `FOF_ALLOWUNDO` apenas preserva informações de desfazer quando possível. A documentação de flags não comprova a operação neste ambiente. Validar também `FOFX_EARLYFAILURE` junto de `FOF_NOERRORUI` e todos os callbacks/cancelamentos.
2. Usar APIs de caminhos Unicode/longos, itens Shell compatíveis e identidade física por handle. Não assumir que uma configuração de política resolve limitações da biblioteca.
3. Consultar atributos e reparse tags por handle. CLOUD conhecida precisa política explícita de hidratação consentida; nesta versão todas são bloqueadas. Tags desconhecidas, links e junctions não podem escapar das raízes.
4. Implementar `recycle_guarded(source,preserved)` com revalidação imediata de identidade, raiz e hashes completos, conforme a política atual. Bloquear mudanças detectadas e declarar a janela residual depois de liberar handles. Não usar cache como autorização. Não prometer atomicidade.
5. Verificar volume local com suporte à reciclagem, resultado nativo de cada item, cancelamento, identidade e ausência original; só então retornar `success` com `native_evidence` e `original_absent`. Falta de prova retorna `uncertain` e exige reconciliação. Nunca mover referência, esvaziar Lixeira ou recorrer a shell/exclusão permanente.
6. Testes opt-in de fixtures Windows: Unicode, >260 caracteres, mudança concorrente durante operação, rede/volume não reciclável, junction, reparse desconhecido, hard links, arquivos CLOUD, falhas parciais, cancelamento, repetição/reinício e restauração pelo SO com hash original. Não usar arquivos pessoais.

## Referências oficiais a verificar

- [IFileOperation](https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nn-shobjidl_core-ifileoperation)
- [SetOperationFlags](https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nf-shobjidl_core-ifileoperation-setoperationflags)
- [IFileOperationProgressSink](https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nn-shobjidl_core-ifileoperationprogresssink)
- [Limitação de caminhos](https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation)
- [Reparse points](https://learn.microsoft.com/en-us/windows/win32/fileio/reparse-points)
- [Cloud Files API](https://learn.microsoft.com/en-us/windows/win32/cfapi/cloud-files-api-portal)

As páginas Learn retornaram **HTTP 403**. Foi possível ler as fontes oficiais atuais no GitHub MicrosoftDocs: [flags](https://github.com/MicrosoftDocs/sdk-api/blob/docs/sdk-api-src/content/shobjidl_core/nf-shobjidl_core-ifileoperation-setoperationflags.md), [PostDeleteItem](https://github.com/MicrosoftDocs/sdk-api/blob/docs/sdk-api-src/content/shobjidl_core/nf-shobjidl_core-ifileoperationprogresssink-postdeleteitem.md), [caminhos longos](https://github.com/MicrosoftDocs/win32/blob/docs/desktop-src/FileIO/maximum-file-path-limitation.md) e [CfHydratePlaceholder](https://github.com/MicrosoftDocs/sdk-api/blob/docs/sdk-api-src/content/cfapi/nf-cfapi-cfhydrateplaceholder.md). Caminhos longos dependem da API e do opt-in do aplicativo, além da configuração do sistema; Shell e filesystem podem divergir. Hidratação é uma operação explícita, não prova de conteúdo local. `PostDeleteItem` fornece o HRESULT por item e informações do destino de reciclagem quando disponíveis.

Essa consulta documental não substitui execução e prova de concorrência. A primeira implementação permaneceu somente no teste básico. Após a prova nativa da 0.2.1 fornecida pelo usuário, a 0.3.0 reaproveita essa camada no adaptador/executor, com habilitação limitada a fixtures. A validação nativa desse fluxo está pendente; o ambiente cloud continua Linux.
