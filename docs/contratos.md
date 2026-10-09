# Contratos v1

Documentos externos JSON têm `schema_version: 1`. IDs são opacos de 32 caracteres hexadecimais. IDs de arquivo são estáveis para caminho/papel dentro da mesma época de configuração; reconfigurar muda essa época. Caminhos são evidência de exibição, nunca autorização enviada para executar.

| Documento | Campos relevantes |
|---|---|
| Configuração | id, source, references[], recursive, root_identities[] |
| Inventário | id, config, status, stage, started_at, finished_at?, bytes_read, summary, errors[], items[] paginados |
| Candidato | id, role, root, path, name, size, mtime_ns, ctime_ns, identity[], metadata_source, state, reason, hash?, hash_source?, matches[], references[], group_id? |
| Grupo | group_id no candidato verificado, hash, conjunto de matches/references; representação embutida no inventário |
| Plano | id, job_id, config, created_at, items[{source,preserved,exception,blocked_reason}], bytes, executable |
| Operação | id (= plano), status, started_at, finished_at?, results[] |
| Resultado | id, path, identity, hash, exception, status, reason?, native_evidence?, original_absent? |
| Erro API | schema_version, code, error (mensagem em português) |

Identidade: `[device, inode, size, mtime_ns, ctime_ns, nlink]`. `ctime` POSIX indica alteração de metadados, não criação. SHA-256 compara somente bytes do fluxo principal. Grupos nunca dão permissão de lote implícita.

Estados de candidato: `pending`, `blocked`, `verified`, `similar`, `unmatched`; referências internas usam `reference`. Job: `running`, `completed`, `cancelled`, `failed`, `invalidated`. Resultado: `intent`, `success`, `blocked`, `failed`, `cancelled`, `uncertain`. Operação concluída não significa todos os itens tiveram sucesso; sempre consulte `results`.

## API

GET `/api/state?offset=0`: capacidades, CSRF de processo, configuração e inventário atual (50 origens/página). GET `/api/history`: até 100 operações recentes com resultados. HTML/CSS/JS são rotas fixas; não há acesso estático arbitrário ao disco.

POST precisa `Content-Type: application/json`, Origin exato e `X-Tidyup-CSRF` da sessão local. Limite 128 KiB. Rotas:

- `/api/config`: `{source, references, recursive}`; valida sem iniciar varredura.
- `/api/scan` e `/api/resume`: `{}`; nova varredura, configuração atual, cache revalidado.
- `/api/cancel`: `{}`; pede interrupção de leituras e de novas operações.
- `/api/shutdown`: `{}`; cancela novas operações e encerra o serviço sem terminal; exige Origin/CSRF.
- `/api/native-diagnostics`: `{}`; diagnóstico COM Windows, sem exclusão ou habilitação de movimentação.
- `/api/plan`: `{selections:[{id,exception:boolean}]}`; uma decisão individual por origem, até 1000. Reler provas detecta mudanças. Não habilita movimentação em produção.
- `/api/execute`: `{plan_id}`; o ID identifica a revisão exata confirmada. Produção retorna bloqueio por adaptador indisponível. O contrato de executor é exercitado somente com adaptadores sintéticos nos testes.

Reconfiguração/rescan invalidam planos para execução. Em caso de erro por mudança, faça novo inventário e nova revisão; não troque itens automaticamente. POST pode retornar 400 para bloqueios de política, 403 para autorização local e 500 para falha interna; mensagens não expõem stack trace. Chamadas concorrentes de execução são serializadas. Reiniciar não recria operações nativas incertas.

## Extensão futura de filtros

Contrato reservado: `{schema_version:1, inventory_id, candidate_ids:[], count, bytes, explanation}`. Filtros ou curingas apenas propõem IDs revisáveis; a seleção individual, revisão e confirmação continuam obrigatórias. Não há endpoint, seleção em massa ou exclusão automática nesta versão. Mudanças incompatíveis exigem nova versão do esquema, migração documentada e revisão de compatibilidade.
