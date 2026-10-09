# Integração futura com PM Cockpit

Este repositório é a fonte única do núcleo. Nenhum acesso ao PM Cockpit foi necessário ou realizado. Não copiar código para uma segunda implementação divergente.

Uma futura versão publicada, revisada e autorizada poderá ser consumida por pacote Python ou por adaptador da API loopback, com versão fixada e contratos v1. Um integrador precisa manter contexto local, raízes explícitas, confirmação da lista exata e todas as políticas do núcleo. A API não deve ser hospedada remotamente nem aceitar caminhos para executar. Autenticação CSRF existente é de uma interface local, não um protocolo para acesso remoto.

Dois desenvolvedores: tarefas pequenas, branches próprias, ambientes/árvores separados, PR com revisão do outro desenvolvedor e testes antes da integração. Tags e publicação só mediante autorização. Contratos mudados exigem changelog, revisão e notas de compatibilidade, incluindo migrações/backups. Nesta entrega não houve push, PR, merge, tag ou publicação.
