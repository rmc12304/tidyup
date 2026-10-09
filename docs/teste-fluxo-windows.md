# Teste do fluxo do executor no Windows — 0.3.0

Este teste liga o Engine real ao adaptador Windows. Usa inventário, seleção por IDs, plano revisado, intenção SQLite e resultados por item. Compartilha a camada IFileOperation com o teste básico que passou na 0.2.1.

## Executar sem terminal

1. Extraia **todo** o pacote `tidyup-local-0.3.0.zip` em uma pasta nova. Requer Windows 8 ou mais recente e Python >=3.12.
2. Dê duplo clique em **Testar Fluxo Windows.cmd**. Isso autoriza somente a execução sobre fixtures novas criadas pelo teste; nenhuma pasta pessoal é recebida ou inventariada.
3. Aguarde a janela de resultado e envie o JSON indicado nela. O relatório fica em `%LOCALAPPDATA%/Tidyup/native-test-reports/windows-flow-<id>.json`.

## O que o teste faz

- Cria cinco arquivos sintéticos e cinco referências, além de um banco próprio, sob uma raiz nova `tidyup-windows-flow-*` em TEMP.
- Inventaria e seleciona dois arquivos, incluindo um nome Unicode. Executa o plano pelo Engine e exige prova de reciclagem por item, ausência original e hash do conteúdo retornado pelo Shell.
- Confere que o arquivo não selecionado e todas as referências foram preservados.
- Repete o ID do plano e reabre o banco em outro Engine: deve retornar o resultado registrado sem movimentar novamente.
- Cria novos planos, altera intencionalmente uma origem e uma referência após a revisão e exige bloqueio das duas operações, com as origens ainda presentes.
- Registra operações e verificações no relatório. O banco mantém intenções/resultados duráveis, inclusive se o processo for interrompido.

Somente `passed` com todas as verificações aprovadas confirma esta execução. Se o resultado for diferente, envie o relatório antes de tentar resolver manualmente ou repetir uma operação incerta. Um novo duplo clique cria outra fixture; nunca reutiliza a anterior.

## Limites e preservação

O teste **não habilita a limpeza normal**, não inicia servidor nem recebe seleções da interface. Usa o mesmo executor/adaptador com uma restrição adicional às raízes da fixture. Não testa interface, restauração, caminhos longos, destinos não recicláveis, cancelamento real durante COM ou toda a matriz Windows.

Não há exclusão permanente, esvaziamento da Lixeira ou limpeza automática das fixtures. Itens reciclados permanecem na Lixeira; referências, itens restantes e banco permanecem em TEMP. Relatórios e dados privados ficam fora do repo/pacote. O teste básico continua disponível em **Testar Lixeira.cmd**.

Na nuvem Linux, os testes do adaptador e deste runner usam uma movimentação reversível simulada. Isso verifica a lógica, sem provar IFileOperation. A execução nativa da 0.3.0 está pendente no Windows do usuário.
