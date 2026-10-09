# Backlog

Atualizado em 2026-10-08. Versão atual: 0.3.0 em desenvolvimento, sem lançamento oficial. Código enviado ao GitHub na branch `main`; validação Windows pendente.

Objetivo: entregar um aplicativo local que abra por duplo clique, revise arquivos e envie somente os itens escolhidos à Lixeira do Windows. O HTML isolado permite visualizar a interface; as operações dependem do componente local.

Prioridades: P0 impede a limpeza operacional; P1 melhora a entrega Windows; P2 melhora o uso após os bloqueios principais. A ordem é uma proposta técnica e pode ser alterada pelo usuário. Itens concluídos saem desta lista e entram no [changelog](../CHANGELOG.md). A sequência ativa fica em [próximos passos](PROXIMOS_PASSOS.md).

| ID | Prioridade | Melhoria / problema | Estado | Critério de conclusão |
|---|---|---|---|---|
| B01 | P0 | Integrar IFileOperation ao adaptador normal e ao executor | Implementado; validação nativa pendente | `recycle_guarded` revalida origem/referência, exige reciclagem e fornece resultado por item; intenção durável e resultados incertos continuam tratados. Integração validada com fixtures, sem ativação automática a partir do teste básico. |
| B02 | P0 | Ampliar validação nativa Windows | Parcial: fixture básica passou; runner do executor pronto | Exercitar Unicode, caminhos longos, mudanças detectadas, cancelamento, falha parcial, repetição/reinício e destinos não recicláveis. Registrar cobertura real e bloquear cenários sem evidência suficiente; nunca usar exclusão permanente. Depende de B01 para validar o fluxo completo. |
| B03 | P0 | Validar restauração pela Lixeira do Windows | Pendente | Restaurar uma fixture pelo SO e conferir localização e SHA-256 original. Registrar o que foi comprovado e as limitações; não prometer restauração universal. |
| B04 | P1 | Validar abertura e ciclo de uso Windows por duplo clique | Parcial: inicializador de teste executado pelo usuário | Abrir, reabrir a mesma instância, inventariar/revisar fixtures, encerrar e reiniciar com dados preservados. Registrar versões e resultados; sem exigir terminal no uso diário. |
| B05 | P1 | Preparar entrega operacional Windows | Bloqueado por B01–B04 | Pacote com instruções coerentes, versão identificável e checksums; documentar plataformas/cenários efetivamente suportados. Publicação requer autorização do usuário. |
| B06 | P2 | Escolher pastas sem digitar caminhos | Pendente | Seleção explícita de origem/referências, com validação das raízes e sem varredura automática de discos. |
| B07 | P2 | Simplificar instalação e dependência de Python | A decidir | Comparar manter o inicializador atual com distribuir executável; usuário escolhe após conhecer tamanho, manutenção e experiência de instalação. |
| B08 | P2 | Melhorar reconciliação de operações incertas | Pendente | Mostrar evidências e orientar conferência sem repetir automaticamente a movimentação; testar recuperação com fixtures. O núcleo já bloqueia a repetição. |
| B09 | P2 | Medir desempenho em volume representativo | Pendente | Benchmark sintético maior com tempo, bytes, memória e condições do cache registrados; sem inferir tempo para pastas pessoais a partir do teste pequeno. |
| B10 | P2 | Auditar acessibilidade da interface | Parcial: teclado e responsividade testados | Conferir contraste e leitor de tela, corrigir falhas e registrar resultados reproduzíveis. |

## Restrições e decisões já tomadas

- Português do Brasil, execução local e abertura simples por duplo clique.
- Revalidar identidade e hashes imediatamente antes da operação; o usuário aceita a janela concorrente após liberar os handles. Não retomar a exigência de atomicidade como bloqueador.
- Somente Lixeira, sem fallback permanente. Referências permanecem intactas. Testes de movimentação usam fixtures.
- O relatório Windows da 0.2.1 confirmou reciclagem, ausência da origem e hashes esperado/reciclado/referência iguais, com Python 3.14.8. Isso conclui a prova básica, sem concluir B01–B05.
- Relatórios brutos e caminhos pessoais ficam fora do repositório e dos pacotes.

Novas ideias devem ter ID, prioridade, estado e critério de conclusão. Não registrar uma hipótese como requisito aprovado nem um teste simulado como validação nativa.
