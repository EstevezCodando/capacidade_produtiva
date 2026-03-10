# CapacidadeProdutiva — Frontend

React 18 + TypeScript + Vite + TanStack Query

## Início rápido

```bash
# 1. Instalar dependências
npm install

# 2. Configurar variáveis de ambiente
cp .env.example .env
# Edite .env — VITE_AUTH_URL se tiver serviço de auth, ou deixe vazio para dev

# 3. Iniciar servidor de dev (com proxy para backend em :3050)
npm run dev
# Abre em http://localhost:5173
```

## Login em modo dev (sem serviço de auth)

Deixe `VITE_AUTH_URL` vazio no `.env`.  
No campo **senha**, cole diretamente um JWT gerado manualmente ou pelo backend.  
O frontend usará esse token para chamar `/api/usuarios/me` e iniciar a sessão.

## Build de produção

```bash
npm run build
# Saída em dist/ — sirva com nginx ou qualquer servidor estático
```

## Estrutura

```
src/
  api/          # Axios client + funções por endpoint
  components/
    layout/     # TopNav, AppShell
    ui/         # EmElaboracao, componentes reutilizáveis
  context/      # AuthContext (sessão JWT)
  pages/        # Uma pasta por tela
    Login/
    Dashboard/
    Perfil/     # Inclui aba Configurações para admin
    MinhaAgenda/
    GerenciarAgendas/
    Operadores/
    BlocosProjeto/
    Atividades/
    Exportar/
  types/        # Interfaces TypeScript espelhando o backend
```

## Variáveis de ambiente

| Variável        | Obrigatório | Descrição |
|-----------------|-------------|-----------|
| `VITE_AUTH_URL` | Não (dev)   | URL base do serviço de autenticação externo |
| `VITE_API_URL`  | Não (dev)   | URL do backend (padrão: proxy Vite → localhost:3050) |
