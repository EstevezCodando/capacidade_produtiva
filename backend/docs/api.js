/* ============================================================
   CapacidadeProdutiva — API Reference JavaScript
   Served statically from /api-docs/api.js
   ============================================================ */

"use strict";

/* ── Route data — reflects exact Python router prefixes + paths ──────────────
   Prefix resolution:
     /api/health           → health.router  (no prefix) + /health
     /api/sync/*           → sync.router    prefix=/sync
     /api/usuarios/*       → usuarios.router prefix=/usuarios
     /api/kpi/*            → kpi.router     prefix=/kpi
     /api/atividades/*     → atividades.router (no prefix)
     /api/distribuicao-*   → atividades.router (no prefix)
     /api/agenda/*         → agenda.router  prefix=/agenda
     /api/capacidade/*     → capacidade.router prefix=/capacidade
     /api/relatorios/*     → relatorios.router prefix=/relatorios
     /api/log/*            → log.router     prefix=/log
   ─────────────────────────────────────────────────────────── */

const GROUPS = [
  /* ── 1. INFRA ──────────────────────────────────────────── */
  {
    id: "infra",
    name: "Infra",
    icon: "◈",
    color: "#34d399",
    routes: [
      {
        method: "GET",
        path: "/api/health",
        auth: "público",
        summary: "Health check",
        desc: "Confirma que o serviço está no ar. Sem autenticação. Usado por load balancers e pelo pipeline de inicialização do Docker.",
        errors: [],
        res: `{ "status": "ok" }`,
      },
      {
        method: "GET",
        path: "/api/sync/status",
        auth: "admin",
        summary: "Status da última sincronização SAP",
        desc: "Retorna timestamps do último pipeline SAP → sap_snapshot → kpi. Os campos sap_snapshot_atualizado_em e kpi_calculado_em são expostos aqui e em todos os endpoints de leitura para indicar staleness à UI.",
        errors: ["401", "403"],
        res: `{
  "sap_snapshot_atualizado_em": "2025-01-04T10:00:00Z",
  "kpi_calculado_em":           "2025-01-04T10:01:12Z",
  "ultima_execucao_status":     "ok"
}`,
      },
      {
        method: "POST",
        path: "/api/sync/executar",
        auth: "admin",
        summary: "Disparar sincronização manual",
        desc: "Aciona o pipeline SAP → sap_snapshot → kpi imediatamente. Corresponde ao botão 'Sincronizar SAP' no painel de configurações. Retorna 202 Accepted — execução ocorre em background.",
        errors: ["401", "403"],
        res: `{ "detail": "sincronizacao enfileirada" }`,
      },
    ],
  },

  /* ── 2. USUÁRIOS ───────────────────────────────────────── */
  {
    id: "usuarios",
    name: "Usuários",
    icon: "◉",
    color: "#60a5fa",
    routes: [
      {
        method: "GET",
        path: "/api/usuarios/me",
        auth: "autenticado",
        summary: "Perfil do usuário autenticado",
        desc: "Retorna os dados do usuário extraídos do JWT e espelhados do auth_snapshot: id, uuid, nome, nome_guerra e flag administrador. Usado pela UI para montar o header e decidir quais abas exibir.",
        errors: ["401"],
        res: `{
  "usuario_id":    7,
  "usuario_uuid":  "a1b2c3d4-...",
  "nome":          "João Silva",
  "nome_guerra":   "Silva",
  "administrador": false
}`,
      },
      {
        method: "GET",
        path: "/api/usuarios",
        auth: "admin",
        summary: "Lista todos os usuários",
        desc: "Listagem paginada de usuários do auth_snapshot. Inclui vínculo com perfil de produção e flag de pendência de agenda. Aba Operadores.",
        errors: ["401", "403"],
        req: `?pagina=1&por_pagina=50`,
        res: `{
  "total": 42,
  "pagina": 1,
  "por_pagina": 50,
  "itens": [
    {
      "id":            1,
      "nome":          "João Silva",
      "nome_guerra":   "Silva",
      "ativo":         true,
      "administrador": false
    }
  ]
}`,
      },
      {
        method: "GET",
        path: "/api/usuarios/{usuario_id}",
        auth: "admin",
        summary: "Detalhe de um usuário",
        desc: "Dados completos do usuário: perfil, pontos acumulados por papel (executor / revisor / corretor) e pendências de agenda.",
        errors: ["401", "403", "404"],
        res: `{
  "id":              1,
  "nome":            "João Silva",
  "nome_guerra":     "Silva",
  "ativo":           true,
  "pontos_executor":  120.5,
  "pontos_revisor":    48.0,
  "pontos_corretor":   12.0,
  "pendencias_agenda": []
}`,
      },
    ],
  },

  /* ── 3. KPI & PRODUÇÃO ─────────────────────────────────── */
  {
    id: "kpi",
    name: "KPI & Produção",
    icon: "◎",
    color: "#fbbf24",
    routes: [
      {
        method: "GET",
        path: "/api/kpi/projetos",
        auth: "autenticado",
        summary: "KPI agregado por projeto ativo",
        desc: "Progresso percentual, pontos totais e pontos concluídos por projeto ativo. Base do Dashboard.",
        errors: ["401"],
        res: `{
  "sap_snapshot_atualizado_em": "2025-01-04T10:00:00Z",
  "kpi_calculado_em":           "2025-01-04T10:01:12Z",
  "projetos": [
    {
      "projeto_id":        1,
      "nome":              "Projeto Alpha",
      "progresso":         0.72,
      "pontos_total":      1000.0,
      "pontos_concluidos":  720.0
    }
  ]
}`,
      },
      {
        method: "GET",
        path: "/api/kpi/projetos/{projeto_id}",
        auth: "autenticado",
        summary: "KPI do projeto por bloco e subfase",
        desc: "Drill-down do projeto: progresso por bloco e subfase com pontos total e concluídos. Aba Blocos do Projeto.",
        errors: ["401", "404"],
        res: `{
  "projeto_id":   1,
  "projeto_nome": "Projeto Alpha",
  "sap_snapshot_atualizado_em": "...",
  "blocos": [
    {
      "bloco_id":   2,
      "bloco_nome": "Bloco Norte",
      "subfases": [
        {
          "subfase_id":        3,
          "subfase_nome":      "Reambulação",
          "progresso":         0.60,
          "pontos_total":      200.0,
          "pontos_concluidos": 120.0
        }
      ]
    }
  ]
}`,
      },
      {
        method: "GET",
        path: "/api/kpi/subfase/{subfase_id}",
        auth: "autenticado",
        summary: "UTs de uma subfase com estado e pontos",
        desc: "Listagem completa das UTs da subfase com estado, ciclo, nota, ocorrência, participantes e pontos distribuídos. Aba Atividades.",
        errors: ["401", "404"],
        res: `{
  "subfase_id":   3,
  "subfase_nome": "Reambulação",
  "sap_snapshot_atualizado_em": "...",
  "uts": [
    {
      "ut_id":             101,
      "estado_ut_subfase": "CONCLUIDA_COM_CORRECAO",
      "ciclo_modelo":      "CICLO_1_PADRAO",
      "nota_qualidade":    7,
      "ocorrencia":        "NOTA_VALIDA",
      "pontos_executor":   5.6,
      "pontos_revisor":    2.6,
      "pontos_corretor":   1.8,
      "nome_executor":     "Silva",
      "nome_revisor":      "Costa",
      "nome_corretor":     "Lima",
      "data_inicio_fluxo": "2025-01-02",
      "data_fim_fluxo":    "2025-01-04"
    }
  ]
}`,
      },
      {
        method: "GET",
        path: "/api/kpi/uts/{ut_id}",
        auth: "autenticado",
        summary: "Detalhe completo de uma UT",
        desc: "Estado completo da UT: ciclo, fluxo, validação de nota, texto da observação, participantes e pontos. data_fim_fluxo é null enquanto a UT não estiver concluída.",
        errors: ["401", "404"],
        res: `{
  "ut_id":             101,
  "ciclo_modelo":      "CICLO_1_PADRAO",
  "estado_ut_subfase": "CONCLUIDA_COM_CORRECAO",
  "concluida":         true,
  "nota_qualidade":    7,
  "texto_qualidade":   "Feições coerentes com a escala",
  "ocorrencia":        "NOTA_VALIDA",
  "data_inicio_fluxo": "2025-01-02",
  "data_fim_fluxo":    "2025-01-04",
  "pontos_ut":         10.0,
  "pontos_executor":   5.6,
  "pontos_revisor":    2.6,
  "pontos_corretor":   1.8,
  "nome_executor":     "Silva",
  "nome_revisor":      "Costa",
  "nome_corretor":     "Lima",
  "sap_snapshot_atualizado_em": "...",
  "kpi_calculado_em":           "..."
}`,
      },
      {
        method: "GET",
        path: "/api/kpi/inconsistencias",
        auth: "admin",
        summary: "Alertas: inconsistências de nota e ciclo",
        desc: "UTs com ocorrência NOTA_AUSENTE, NOTA_INVALIDA, INCONSISTENTE_CICLO ou INCONSISTENTE_DIFICULDADE. Alimenta notificações ao gerente. UTs com dificuldade=0 aparecem aqui — não somem silenciosamente.",
        errors: ["401", "403"],
        res: `{
  "total": 3,
  "sap_snapshot_atualizado_em": "...",
  "itens": [
    {
      "ut_id":         55,
      "ocorrencia":    "NOTA_AUSENTE",
      "ciclo_modelo":  "CICLO_1_PADRAO",
      "projeto_nome":  "Projeto Alpha",
      "subfase_nome":  "Reambulação",
      "nome_executor": "Silva"
    }
  ]
}`,
      },
    ],
  },

  /* ── 4. ATIVIDADES ─────────────────────────────────────── */
  {
    id: "atividades",
    name: "Atividades",
    icon: "◇",
    color: "#a78bfa",
    routes: [
      {
        method: "GET",
        path: "/api/atividades",
        auth: "autenticado",
        summary: "Listagem filtrada de atividades",
        desc: "Atividades do snapshot com filtros combináveis. Paginada. Aba Atividades.",
        errors: ["401", "422"],
        req: `?projeto_id=1&usuario_id=7&tipo_situacao_id=4&pagina=1&por_pagina=50`,
        res: `{
  "total":      200,
  "pagina":       1,
  "por_pagina":  50,
  "itens": [
    {
      "id":                 1,
      "ut_id":            101,
      "tipo_etapa_id":      1,
      "tipo_etapa_nome":   "Execução",
      "tipo_situacao_id":   4,
      "tipo_situacao_nome":"Finalizada",
      "usuario_id":         7,
      "usuario_nome":      "Silva",
      "data_inicio":       "2025-01-02",
      "data_fim":          "2025-01-03"
    }
  ]
}`,
      },
      {
        method: "GET",
        path: "/api/atividades/{atividade_id}",
        auth: "autenticado",
        summary: "Detalhe de uma atividade",
        desc: "Atividade completa com nota parseada do campo observacao (formato 'N; texto livre') e texto de qualidade extraído.",
        errors: ["401", "404"],
        res: `{
  "id":                 1,
  "ut_id":            101,
  "tipo_etapa_id":      3,
  "tipo_etapa_nome":   "Correção",
  "tipo_situacao_id":   4,
  "tipo_situacao_nome":"Finalizada",
  "usuario_id":         9,
  "usuario_nome":      "Lima",
  "data_inicio":       "2025-01-03",
  "data_fim":          "2025-01-04",
  "observacao":        "7; Feições coerentes com a escala",
  "nota_qualidade":    7,
  "texto_qualidade":   "Feições coerentes com a escala"
}`,
      },
      {
        method: "GET",
        path: "/api/distribuicao-pontos",
        auth: "autenticado",
        summary: "Distribuição de pontos por UT concluída",
        desc: "Visão wide desnormalizada (tabela kpi.distribuicao_pontos): por UT concluída exibe executor / revisor / corretor com nome e pontos calculados pelas fórmulas do ciclo. Filtros: projeto_id, subfase_id, usuario_id.",
        errors: ["401"],
        req: `?subfase_id=3`,
        res: `{
  "total":   42,
  "sap_snapshot_atualizado_em": "...",
  "itens": [
    {
      "projeto_nome":  "Projeto Alpha",
      "subfase_nome":  "Reambulação",
      "ut_id":         101,
      "pontos_ut":      10.0,
      "ciclo_modelo":  "CICLO_1_PADRAO",
      "nota":           7,
      "nota_valida":    true,
      "nome_executor": "Silva",  "pontos_executor":  5.6,
      "nome_revisor":  "Costa",  "pontos_revisor":   2.6,
      "nome_corretor": "Lima",   "pontos_corretor":  1.8
    }
  ]
}`,
      },
    ],
  },

  /* ── 5. AGENDA ─────────────────────────────────────────── */
  {
    id: "agenda",
    name: "Agenda",
    icon: "▣",
    color: "#f472b6",
    routes: [
      {
        method: "GET",
        path: "/api/agenda/minha",
        auth: "autenticado",
        summary: "Agenda do usuário autenticado",
        desc: "Retorna apontamentos e planejamento do usuário no intervalo solicitado. Inclui status do dia (ABERTO / CONSOLIDADO), tetos e minutos apontados por tipo. Aba Minha Agenda.",
        errors: ["401", "422"],
        req: `?data_inicio=2025-01-01&data_fim=2025-01-31`,
        res: `{
  "usuario_id": 7,
  "dias": [
    {
      "data":                "2025-01-06",
      "status":              "ABERTO",
      "teto_normal_min":     360,
      "teto_extra_min":      600,
      "apontado_normal_min": 300,
      "apontado_extra_min":    0,
      "apontamentos": [
        {
          "id":         12,
          "bloco_id":    2,
          "bloco_nome": "Bloco Norte",
          "minutos":    180,
          "tipo":       "normal"
        }
      ]
    }
  ]
}`,
      },
      {
        method: "POST",
        path: "/api/agenda/minha/apontamento",
        auth: "autenticado",
        summary: "Lançar apontamento próprio",
        desc: "Registra apontamento do usuário autenticado. Dia futuro é bloqueado. Dia CONSOLIDADO rejeita normal e aceita extra com alerta. Feriados só aceitam extra.",
        errors: ["401", "422"],
        req: `{
  "data":     "2025-01-06",
  "bloco_id": 2,
  "minutos":  120,
  "tipo":     "normal"
}`,
        res: `{
  "id":      99,
  "data":    "2025-01-06",
  "minutos": 120,
  "tipo":    "normal",
  "alertas": []
}`,
      },
      {
        method: "PUT",
        path: "/api/agenda/minha/apontamento/{apontamento_id}",
        auth: "autenticado",
        summary: "Editar apontamento próprio",
        desc: "Edita apontamento em dia ABERTO com log de auditoria. Dia CONSOLIDADO bloqueia edição de normal.",
        errors: ["401", "404", "422"],
        req: `{ "minutos": 150 }`,
        res: `{ "id": 99, "minutos": 150, "alertas": [] }`,
      },
      {
        method: "DELETE",
        path: "/api/agenda/minha/apontamento/{apontamento_id}",
        auth: "autenticado",
        summary: "Remover apontamento próprio",
        desc: "Remove apontamento em dia ABERTO. Dia CONSOLIDADO bloqueia a remoção.",
        errors: ["401", "404"],
        res: `{ "removido": true }`,
      },
      {
        method: "GET",
        path: "/api/agenda/usuarios/{usuario_id}",
        auth: "admin",
        summary: "Agenda de um usuário (admin)",
        desc: "Admin visualiza agenda completa de qualquer operador: planejamento e apontamentos realizados. Aba Gerenciar Agendas.",
        errors: ["401", "403", "404"],
        req: `?data_inicio=2025-01-01&data_fim=2025-01-31`,
        res: `{ "usuario_id": 7, "dias": [ ... ] }`,
      },
      {
        method: "POST",
        path: "/api/agenda/usuarios/{usuario_id}/apontamento",
        auth: "admin",
        summary: "Lançar apontamento por um usuário (admin)",
        desc: "Admin lança apontamento em nome de operador. Permite datas passadas já consolidadas com alerta registrado na trilha de auditoria.",
        errors: ["401", "403", "422"],
        req: `{
  "data":     "2025-01-06",
  "bloco_id": 2,
  "minutos":  120,
  "tipo":     "normal"
}`,
        res: `{
  "id":      100,
  "data":    "2025-01-06",
  "minutos": 120,
  "tipo":    "normal",
  "alertas": ["Dia consolidado — alteração registrada em auditoria"]
}`,
      },
      {
        method: "GET",
        path: "/api/agenda/planejamento",
        auth: "admin",
        summary: "Agenda planejada de todos os operadores",
        desc: "Planejamento de todos os operadores no intervalo. Aba Gerenciar Agendas.",
        errors: ["401", "403", "422"],
        req: `?data_inicio=2025-01-01&data_fim=2025-01-31`,
        res: `{
  "operadores": [
    { "usuario_id": 3, "dias": [ ... ] }
  ]
}`,
      },
      {
        method: "POST",
        path: "/api/agenda/planejamento",
        auth: "admin",
        summary: "Lançar ou atualizar planejamento",
        desc: "Admin define agenda planejada de um operador para datas futuras.",
        errors: ["401", "403", "422"],
        req: `{
  "usuario_id":         3,
  "data":               "2025-02-03",
  "bloco_id":           2,
  "minutos_planejados": 360
}`,
        res: `{ "id": 88 }`,
      },
    ],
  },

  /* ── 6. CAPACIDADE ─────────────────────────────────────── */
  {
    id: "capacidade",
    name: "Capacidade",
    icon: "◰",
    color: "#34d399",
    routes: [
      {
        method: "GET",
        path: "/api/capacidade/config",
        auth: "admin",
        summary: "Configuração do teto diário",
        desc: "Teto normal e extra vigentes, quem configurou e quando. Ajustável pelo gerente em Configurações.",
        errors: ["401", "403"],
        res: `{
  "teto_normal_min": 360,
  "teto_extra_min":  600,
  "configurado_em":  "2025-01-01T08:00:00Z",
  "configurado_por": "gerente@cp.local"
}`,
      },
      {
        method: "PUT",
        path: "/api/capacidade/config",
        auth: "admin",
        summary: "Atualizar teto diário",
        desc: "Atualiza o teto normal e extra. Alteração é registrada no schema log.",
        errors: ["401", "403", "422"],
        req: `{
  "teto_normal_min": 420,
  "teto_extra_min":  600
}`,
        res: `{
  "teto_normal_min": 420,
  "teto_extra_min":  600,
  "configurado_em":  "2025-03-10T09:00:00Z",
  "configurado_por": "gerente@cp.local"
}`,
      },
      {
        method: "GET",
        path: "/api/capacidade/status",
        auth: "admin",
        summary: "Status dos dias num intervalo",
        desc: "Status ABERTO ou CONSOLIDADO de cada dia do intervalo para todos os usuários ativos.",
        errors: ["401", "403", "422"],
        req: `?data_inicio=2025-01-01&data_fim=2025-01-31`,
        res: `{
  "dias": [
    { "data": "2025-01-06", "status": "ABERTO"      },
    { "data": "2025-01-07", "status": "CONSOLIDADO" }
  ]
}`,
      },
      {
        method: "POST",
        path: "/api/capacidade/consolidar",
        auth: "admin",
        summary: "Consolidar intervalo de datas",
        desc: "Valida se todos os usuários ativos lançaram horas normais no intervalo. Se houver pendências, retorna lista por usuário e dia — consolidação só ocorre sem pendências.",
        errors: ["401", "403", "422"],
        req: `{
  "data_inicio": "2025-01-01",
  "data_fim":    "2025-01-31"
}`,
        res: `{
  "consolidado": false,
  "mensagem":    "3 pendências encontradas",
  "pendencias": [
    {
      "usuario_id":     3,
      "nome":           "Costa",
      "dias_pendentes": ["2025-01-08", "2025-01-15"]
    }
  ]
}`,
      },
      {
        method: "GET",
        path: "/api/capacidade/feriados",
        auth: "autenticado",
        summary: "Lista feriados cadastrados",
        desc: "Feriados e indisponibilidades globais. Em dias de feriado somente lançamentos do tipo extra são aceitos.",
        errors: ["401"],
        res: `{
  "feriados": [
    { "id": 1, "data": "2025-01-01", "descricao": "Ano Novo"    },
    { "id": 2, "data": "2025-04-21", "descricao": "Tiradentes"  }
  ]
}`,
      },
      {
        method: "POST",
        path: "/api/capacidade/feriados",
        auth: "admin",
        summary: "Cadastrar feriado ou indisponibilidade",
        desc: "Admin cadastra feriado global. Dias afetados passam a aceitar somente lançamentos extra.",
        errors: ["401", "403", "422"],
        req: `{
  "data":      "2025-04-21",
  "descricao": "Tiradentes"
}`,
        res: `{ "id": 5, "data": "2025-04-21", "descricao": "Tiradentes" }`,
      },
      {
        method: "DELETE",
        path: "/api/capacidade/feriados/{feriado_id}",
        auth: "admin",
        summary: "Remover feriado",
        desc: "Remove um feriado. Dias antes bloqueados voltam a aceitar lançamentos normais.",
        errors: ["401", "403", "404"],
        res: `{ "removido": true }`,
      },
    ],
  },

  /* ── 7. RELATÓRIOS ─────────────────────────────────────── */
  {
    id: "relatorios",
    name: "Relatórios",
    icon: "◫",
    color: "#e879f9",
    routes: [
      {
        method: "GET",
        path: "/api/relatorios/capacidade",
        auth: "autenticado",
        summary: "Relatório de capacidade por operador",
        desc: "Horas planejadas vs realizadas por operador no período com saldo. Aba Exportar.",
        errors: ["401", "422"],
        req: `?data_inicio=2025-01-01&data_fim=2025-01-31&usuario_id=7`,
        res: `{
  "data_inicio": "2025-01-01",
  "data_fim":    "2025-01-31",
  "itens": [
    {
      "usuario_id":           7,
      "nome":                 "Silva",
      "horas_planejadas_min": 1440,
      "horas_realizadas_min": 1320,
      "saldo_min":            -120
    }
  ]
}`,
      },
      {
        method: "GET",
        path: "/api/relatorios/producao",
        auth: "autenticado",
        summary: "Relatório de produção por operador",
        desc: "Pontos e UTs concluídas por operador no período, com distribuição por papel (executor / revisor / corretor). Aba Exportar.",
        errors: ["401", "422"],
        req: `?data_inicio=2025-01-01&data_fim=2025-01-31`,
        res: `{
  "data_inicio": "2025-01-01",
  "data_fim":    "2025-01-31",
  "itens": [
    {
      "usuario_id":      7,
      "nome":            "Silva",
      "pontos_executor": 80.2,
      "pontos_revisor":  30.1,
      "pontos_corretor": 10.0,
      "uts_concluidas":  12
    }
  ]
}`,
      },
      {
        method: "GET",
        path: "/api/relatorios/progresso-blocos",
        auth: "autenticado",
        summary: "Progresso por bloco e subfase",
        desc: "Avanço percentual por bloco e subfase com pontos total e concluídos. Aba Blocos do Projeto.",
        errors: ["401", "422"],
        req: `?projeto_id=1`,
        res: `{
  "projeto_id":   1,
  "projeto_nome": "Projeto Alpha",
  "sap_snapshot_atualizado_em": "...",
  "blocos": [
    {
      "bloco_id":   2,
      "bloco_nome": "Bloco Norte",
      "progresso":  0.65,
      "subfases": [
        {
          "subfase_id":        3,
          "subfase_nome":      "Reambulação",
          "progresso":         0.60,
          "pontos_total":      200.0,
          "pontos_concluidos": 120.0
        }
      ]
    }
  ]
}`,
      },
    ],
  },

  /* ── 8. LOG & AUDITORIA ─────────────────────────────────── */
  {
    id: "log",
    name: "Log & Auditoria",
    icon: "⬟",
    color: "#94a3b8",
    routes: [
      {
        method: "GET",
        path: "/api/log/sync",
        auth: "admin",
        summary: "Histórico de execuções do pipeline",
        desc: "Log de cada execução do pipeline SAP → sap_snapshot → kpi: timestamp de início/fim, duração, tabelas afetadas e erros. Paginado.",
        errors: ["401", "403"],
        req: `?pagina=1&por_pagina=20`,
        res: `{
  "total": 144,
  "execucoes": [
    {
      "id":               1,
      "iniciado_em":      "2025-01-04T10:00:00Z",
      "concluido_em":     "2025-01-04T10:00:12Z",
      "duracao_s":        12.3,
      "status":           "ok",
      "tabelas_afetadas": ["sap_snapshot.atividade", "kpi.estado_ut"],
      "erro":             null
    }
  ]
}`,
      },
      {
        method: "GET",
        path: "/api/log/agenda",
        auth: "admin",
        summary: "Auditoria de apontamentos",
        desc: "Trilha de criação, edição e remoção de apontamentos com usuário responsável, timestamp e detalhe. Filtros: usuario_id, data_inicio, data_fim.",
        errors: ["401", "403"],
        req: `?usuario_id=3&data_inicio=2025-01-01&data_fim=2025-01-31`,
        res: `{
  "total": 28,
  "eventos": [
    {
      "id":                 1,
      "acao":               "criado",
      "apontamento_id":    99,
      "usuario_id":         3,
      "realizado_por_id":   1,
      "realizado_por_nome": "gerente",
      "em":                 "2025-01-06T08:30:00Z",
      "detalhe":            "Lançamento em dia consolidado"
    }
  ]
}`,
      },
    ],
  },
];

/* ── Helpers ─────────────────────────────────────────────────────────────── */

const TOTAL = GROUPS.reduce((acc, g) => acc + g.routes.length, 0);

function formatPath(path) {
  return path.replace(/\{([^}]+)\}/g, '<span class="param">{$1}</span>');
}

function authClass(auth) {
  return { "público": "auth-pub", "autenticado": "auth-tok", "admin": "auth-adm" }[auth] ?? "auth-pub";
}

const ERROR_META = {
  "401": { cls: "e-401", label: "401 Unauthorized" },
  "403": { cls: "e-403", label: "403 Forbidden" },
  "404": { cls: "e-404", label: "404 Not Found" },
  "422": { cls: "e-422", label: "422 Validation Error" },
};

function errorChip(code) {
  const m = ERROR_META[code] ?? { cls: "e-401", label: code };
  return `<span class="error-chip ${m.cls}">${m.label}</span>`;
}

/* ── Build DOM ───────────────────────────────────────────────────────────── */

function buildSidebar() {
  const aside = document.getElementById("sidebar");
  const section = document.createElement("div");
  section.className = "sidebar-section";
  section.innerHTML = `<div class="sidebar-section-label">Grupos</div>`;
  GROUPS.forEach(g => {
    const a = document.createElement("a");
    a.className = "sidebar-link";
    a.href = `#group-${g.id}`;
    a.dataset.group = g.id;
    a.innerHTML = `
      <span class="sidebar-link-dot" style="background:${g.color}"></span>
      <span>${g.name}</span>
      <span class="sidebar-count">${g.routes.length}</span>`;
    section.appendChild(a);
  });
  aside.appendChild(section);
}

function buildRouteCard(route, gIdx, rIdx) {
  const key = `${gIdx}-${rIdx}`;
  const isQuery = route.method === "GET";
  const hasReq = !!route.req;

  const card = document.createElement("div");
  card.className = "route-card";
  card.id = `card-${key}`;
  card.dataset.auth = route.auth;
  card.dataset.text = `${route.path} ${route.summary} ${route.desc}`.toLowerCase();

  card.innerHTML = `
    <button class="route-row" aria-expanded="false">
      <span class="method method-${route.method}">${route.method}</span>
      <code class="route-path">${formatPath(route.path)}</code>
      <span class="route-summary">${route.summary}</span>
      <span class="auth-badge ${authClass(route.auth)}">${route.auth}</span>
      <span class="chevron">▾</span>
    </button>
    <div class="detail">
      <p class="detail-desc">${route.desc}</p>
      <div class="detail-blocks">
        ${hasReq ? `
        <div>
          <div class="block-label">${isQuery ? "query params" : "request body"}</div>
          <pre class="code-pre code-req">${route.req}</pre>
        </div>` : ""}
        <div>
          <div class="block-label">response 200</div>
          <pre class="code-pre code-res">${route.res}</pre>
        </div>
        ${route.errors.length ? `
        <div>
          <div class="block-label">possíveis erros</div>
          <div class="errors-list">${route.errors.map(errorChip).join("")}</div>
        </div>` : ""}
      </div>
    </div>`;

  card.querySelector(".route-row").addEventListener("click", () => {
    const isOpen = card.classList.toggle("open");
    card.querySelector(".route-row").setAttribute("aria-expanded", isOpen);
  });

  return card;
}

function buildContent() {
  const content = document.getElementById("content");

  GROUPS.forEach((g, gi) => {
    const section = document.createElement("section");
    section.className = "group";
    section.id = `group-${g.id}`;
    section.style.setProperty("--group-color", g.color);

    const header = document.createElement("div");
    header.className = "group-header";
    header.innerHTML = `
      <span class="group-icon" style="color:${g.color}">${g.icon}</span>
      <span class="group-name">${g.name}</span>
      <span class="group-count">${g.routes.length}</span>`;
    section.appendChild(header);

    const list = document.createElement("div");
    list.className = "routes";
    g.routes.forEach((r, ri) => list.appendChild(buildRouteCard(r, gi, ri)));
    section.appendChild(list);
    content.appendChild(section);
  });

  document.getElementById("empty-state").style.display = "none";
}

/* ── Filter & Search ─────────────────────────────────────────────────────── */

let currentAuth = "todos";
let currentSearch = "";

function applyFilter() {
  let visible = 0;

  GROUPS.forEach((g, gi) => {
    const section = document.getElementById(`group-${g.id}`);
    let groupVisible = 0;

    g.routes.forEach((_, ri) => {
      const card = document.getElementById(`card-${gi}-${ri}`);
      const matchAuth = currentAuth === "todos" || card.dataset.auth === currentAuth;
      const matchSearch = currentSearch === "" || card.dataset.text.includes(currentSearch);
      const show = matchAuth && matchSearch;
      card.classList.toggle("hidden", !show);
      if (show) { groupVisible++; visible++; }
    });

    section.classList.toggle("hidden", groupVisible === 0);
  });

  document.getElementById("toolbar-result").textContent = `${visible} / ${TOTAL} rotas`;

  const emptyState = document.getElementById("empty-state");
  const anyGroup = document.querySelector(".group:not(.hidden)");
  emptyState.style.display = anyGroup ? "none" : "block";
}

/* ── Sidebar active link on scroll ──────────────────────────────────────── */

function setupScrollSpy() {
  const observer = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        const id = e.target.id.replace("group-", "");
        document.querySelectorAll(".sidebar-link").forEach(a => {
          a.classList.toggle("active", a.dataset.group === id);
        });
      }
    });
  }, { rootMargin: "-30% 0px -60% 0px" });

  document.querySelectorAll(".group").forEach(s => observer.observe(s));
}

/* ── Wire up controls ────────────────────────────────────────────────────── */

function setup() {
  buildSidebar();
  buildContent();

  document.getElementById("total-count").textContent = `${TOTAL} rotas`;
  document.getElementById("toolbar-result").textContent = `${TOTAL} / ${TOTAL} rotas`;

  document.getElementById("search").addEventListener("input", e => {
    currentSearch = e.target.value.trim().toLowerCase();
    applyFilter();
  });

  document.querySelectorAll(".filter-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentAuth = btn.dataset.auth;
      applyFilter();
    });
  });

  setupScrollSpy();
}

document.addEventListener("DOMContentLoaded", setup);
