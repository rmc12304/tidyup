# Dados, retenção e recuperação

`DATA_DIR` não pode estar no repositório nem dentro/acima de origem ou referências. SQLite armazena caminhos pessoais, preferências/configuração, backups das configurações anteriores, cache, inventário atual, planos e histórico. Nunca adicione o banco ao Git. Não publique logs ou screenshots de um inventário pessoal. O app não transmite nomes/conteúdos; o operador é responsável por backups locais e permissões.

Retenção inicial é manual e sem prazo fixo. Cache e inventário podem ser descartados depois de backup; auditoria/planos de resultados incertos precisam ser preservados até reconciliação. Não apague só arquivos WAL/SHM: eles fazem parte do estado SQLite ativo. Não existe botão de expiração ou de reconciliação automática nesta versão.

## Backup e mudar DATA_DIR

1. Cancele operações, encerre o serviço com Ctrl+C e confirme a saída do processo.
2. Faça cópia de backup de **todo** DATA_DIR, preservando permissões. Sem processo ativo, copie também eventuais WAL/SHM. Proteja o backup como dados pessoais.
3. Copie para outro diretório dedicado fora de raízes/repositório. Inicie com `--data-dir` apontando para ele. Valide a configuração e execute novo inventário antes de revisar.
4. Mantenha a cópia anterior até verificar o histórico e a integridade do estado. Não execute duas instâncias contra o mesmo banco; isto não é um banco multioperador.

## Migração e rollback

O esquema atual é 1. O programa recusa esquemas desconhecidos. Não há migração na versão inicial. Qualquer atualização de esquema deve ter migração, backup prévio obrigatório e instruções de rollback testadas. Para rollback de uma futura versão ainda compatível com esquema 1: encerre, preserve um backup integral do estado atual, volte ao checkout autorizado anterior compatível (0.1.0) e use o estado esquema 1. Se uma atualização tiver migrado o banco, restaure somente um backup pré-migração compatível; não force `PRAGMA user_version`.

Um rollback de código/banco **não restaura arquivos** nem desfaz operações do SO. Se existirem movimentações depois do backup, restaurar o banco pode perder evidências: preserve a auditoria atual e reconcilie manualmente antes de habilitar novas operações. O executor de produção está bloqueado nesta versão.

## Resultados incertos e Lixeira futura

Uma intenção persistida sem prova nativa não é sucesso nem autorização para tentar de novo. Após reinício vira `uncertain`; IDs repetidos retornam o registro anterior e identidade/localização ficam bloqueadas para novos planos. Preserve banco e plano e investigue no sistema operacional. Não recrie automaticamente o arquivo, não repita movimento e não remova o bloqueio editando SQLite. A reconciliação administrativa ainda não foi implementada; nesse caso procure o responsável técnico por um procedimento explícito e revisado.

Quando um adaptador estiver validado, restauração será pelo mecanismo de Lixeira do SO (no Windows, abrir Lixeira e usar Restaurar no item correto), seguida de comparação do hash. Pode haver conflito de nome, política de retenção, limpeza externa ou efeitos de sincronização; não há garantia de recuperação nem prazo fixo. A atualização visual do ícone no Explorer pode atrasar e não serve de prova técnica. Cancelar impede novas operações, não desfaz itens já movidos.
