# Teste real de envio à Lixeira (somente fixture)

## Abrir sem terminal

Em Windows nativo (8 ou mais recente), com Python >=3.12: extraia todo o ZIP e dê duplo clique em **Testar Lixeira.cmd**. Abrir esse inicializador é o opt-in explícito. Não precisa escolher Downloads ou informar caminhos.

O teste cria um arquivo sintético novo e uma referência idêntica numa pasta própria em TEMP. Não recebe caminhos de arquivos pessoais, não varre Lixeira nem discos e não opera as raízes configuradas no aplicativo. Nunca esvazia a Lixeira ou usa fallback de exclusão permanente. Mantenha os resultados para análise; as fixtures não são limpas por exclusão permanente.

## O que é verificado

1. Identidade e SHA-256 completos de origem/referência. Os hashes são conferidos novamente no callback PreDeleteItem, liberando os handles antes da operação conforme a política aceita pelo usuário.
2. Intenção durável antes da chamada nativa. IFileOperation recebe RECYCLEONDELETE, EARLYFAILURE, NOERRORUI, NORECURSION e NOCONFIRMATION. Solicita uma única operação de DeleteItem, seguida de PerformOperations.
3. HRESULT da operação efetiva por item (PostDeleteItem), GetAnyOperationsAborted e item reciclado retornado pelo Shell. DeleteItem sozinho apenas agenda, não comprova sucesso.
4. Ausência da origem **junto** da evidência nativa de reciclagem, hash dos bytes do item retornado e referência intacta. Sem todas as provas, não informa sucesso. A ausência isolada resulta em `uncertain`.

Só `passed` comprova esta fixture. `failed`, `blocked`, `cancelled`, `uncertain` e `not_executed` são resultados distintos. Uma aprovação básica não valida long paths, nuvem, lotes, restauração ou todo o adaptador de produção, nem habilita automaticamente o aplicativo.

## Relatório e recuperação

A janela final indica o resultado e o arquivo JSON em `%LOCALAPPDATA%/Tidyup/native-test-reports`. O relatório contém caminhos da fixture, hashes, flags, HRESULT e callbacks. Dados ficam fora do repositório; não incluir relatórios no ZIP/Git. Um processo interrompido pode deixar `intent`: não repetir aquela mesma operação; preservar/reconciliar o resultado.

A fixture reciclada permanece na Lixeira e a referência em TEMP. Se quiser restaurar, use a Lixeira do Windows e confira o item sintético pelo nome/ID/conteúdo. Restauração automática ou pelo SO **não foi testada**. Não é garantida e não há prazo fixo. O teste deixa uma cópia de referência para conferência, não esvazia nem modifica outros itens.

## Resultado neste ambiente

Na 0.2.1, a comparação de caminho/descritor foi corrigida para considerar a mesma data de criação no Windows. A verificação do descritor antes/depois preserva ChangeTime para bloquear alterações durante leitura. A diferença entre as representações é documentada no código oficial do [CPython posixmodule.c](https://github.com/python/cpython/blob/3.14/Modules/posixmodule.c) e [fileutils.c](https://github.com/python/cpython/blob/3.14/Python/fileutils.c).

O primeiro relatório fornecido pelo usuário ficou `uncertain` por esse erro de verificação. Um segundo relatório, com Tidyup 0.2.1 e Python 3.14.8 no Windows do usuário, confirmou `passed`: pré-validação aprovada, operação nativa sem cancelamento, item reciclado retornado, origem ausente e hashes esperado/reciclado/referência iguais. A correção e a reciclagem básica estão confirmadas. Restauração e adaptador operacional completo permanecem pendentes. Nenhum relatório bruto ou caminho privado foi incorporado ao repositório.

O ambiente de desenvolvimento é Linux, sem Wine, PowerShell ou uma sessão Windows acessível. A execução do runner foi registrada como `not_executed`: nenhuma chamada Windows nem movimentação aconteceu aqui. Foram aprovados testes sintéticos de classificação/callbacks/flags e recusa da plataforma; não são prova de reciclagem nativa.

Os GUIDs, a ordem da vtable e as assinaturas de IFileOperation/IFileOperationProgressSink foram conferidos no [header oficial do SDK](https://github.com/microsoft/win32metadata/blob/main/generation/WinSDK/RecompiledIdlHeaders/um/ShObjIdl_core.h), além das páginas de [DeleteItem](https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nf-shobjidl_core-ifileoperation-deleteitem) e [PostDeleteItem](https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nf-shobjidl_core-ifileoperationprogresssink-postdeleteitem). Essa conferência documental não substitui execução em Windows.
