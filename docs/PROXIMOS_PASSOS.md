# Próximos passos

Atualizado em 2026-10-08. Integração 0.3.0 implementada e testada sinteticamente na nuvem. Primeiro commit e push para `main` concluídos; o código pode ser acessado por outras sessões conectadas ao repo. A próxima ação funcional é executar o runner do fluxo no Windows; limpeza normal ainda bloqueada.

## Ordem proposta

1. **B01 — implementação concluída; validação pendente.** Camada COM compartilhada, adaptador com revalidação e provas por item conectado ao Engine via runner de fixtures. Na nuvem, 60 testes passaram; simulações não comprovam operação Windows. Não habilitar limpeza comum ainda.
2. **B02 — executar Testar Fluxo Windows.cmd.** Pacote 0.3.0 preparado por Codex; usuário executa no Windows e envia o relatório. Testa lote com Unicode, seleção, referência/item não selecionado preservados, alterações após plano, repetição e reabertura do banco. Veja [procedimento](teste-fluxo-windows.md). Falha encontrada deve virar correção priorizada antes de ampliar a matriz.
3. **B02 restante, B03 e B04 — ampliar validação.** Preparar testes de cancelamento/falha parcial reais, caminhos longos e destinos não recicláveis; conferir restauração e interface/inicializadores no Windows. Não pedir ao usuário decisões técnicas rotineiras ou uso de arquivos pessoais.
4. **B05 — preparar a entrega operacional.** Consolidar evidências, corrigir limitações e gerar pacote para revisão. Publicação depende da decisão do usuário.

## Bloqueios atuais

| Bloqueio | Como remover | Evidência necessária |
|---|---|---|
| Adaptador normal ainda desabilitado | Validar o runner 0.3.0 e ampliar cobertura B02; implementação B01 pronta para essa validação | Revisão do contrato, testes do executor e resultados nativos por item |
| Ambiente cloud sem Windows | Preparar testes locais simples; usuário executa no Windows | Relatórios reais fornecidos pelo usuário; mocks não substituem execução nativa |
| Restauração não testada | Executar B03 apenas com fixture | Conteúdo restaurado com hash e localização conferidos |

O teste básico da Lixeira e a correção de metadados **já foram confirmados** no relatório da 0.2.1; não são bloqueios pendentes.

## Decisões para o usuário

O usuário confirmou avançar a integração Windows na nuvem. Não há decisão de produto necessária nesta etapa: a próxima participação é executar o teste nativo por duplo clique.

- **Prioridade de produto:** recomendação atual é concluir a limpeza Windows antes de seletor de pastas ou empacotamento sem Python. O usuário pode mudar a ordem; enquanto isso, esta é a sequência proposta.
- **Distribuição (B07):** decidir entre manter Python instalado e um executável quando houver comparação concreta de tamanho, instalação e manutenção. Não é necessário decidir agora.
- **Publicação (B05):** revisar a entrega e autorizar publicação somente quando houver pacote e evidências para avaliar.

Decisões de implementação rotineiras ficam com Codex. Quando uma escolha afetar experiência, escopo ou distribuição, Codex apresenta recomendação, alternativas e consequências; registra a resposta aqui e no backlog.

## Rotina proativa

No início de cada tarefa, consultar estes passos e o backlog. Ao concluir trabalho, atualizar estados, evidências e changelog, retirar bloqueios resolvidos e indicar a próxima ação. Informar ao usuário o resultado, o bloqueio real e eventual decisão necessária, sem pedir que ele gerencie a lista. A atualização ocorre durante o trabalho nesta conversa/repositório; não há monitoramento automático entre sessões.
