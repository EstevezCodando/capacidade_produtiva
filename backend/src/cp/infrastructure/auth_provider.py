"""Provedor de autenticação — abstração para integração com servico_autenticacao.

Este módulo implementa o padrão Strategy para autenticação, permitindo:
- Em produção: integração real com o servico_autenticacao
- Em testes (CI): mock que não depende de serviços externos

A interface AuthProvider define o contrato:
- autenticar_usuario(): valida credenciais e retorna token
- validar_token(): verifica assinatura JWT e retorna contexto do usuário
- obter_dados_usuario(): busca informações adicionais do usuário autenticado

Uso:
    from cp.infrastructure.auth_provider import criar_auth_provider

    provider = criar_auth_provider(settings)
    usuario = provider.validar_token(token)
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

import jwt
import jwt.exceptions

if TYPE_CHECKING:
    from cp.config.settings import Settings

_logger = logging.getLogger(__name__)

# Algoritmo fixo — mesmo usado pelo servico_autenticacao
_ALGORITMO = "HS256"


# ---------------------------------------------------------------------------
# Exceções
# ---------------------------------------------------------------------------


class AuthError(Exception):
    """Erro base de autenticação."""


class TokenInvalido(AuthError):
    """Token ausente, expirado ou com assinatura inválida."""


class CredenciaisInvalidas(AuthError):
    """Usuário ou senha inválidos."""


class ServicoIndisponivel(AuthError):
    """Serviço de autenticação inacessível."""


# ---------------------------------------------------------------------------
# Modelo de dados
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UsuarioAutenticado:
    """Contexto do usuário extraído do JWT após validação.

    Campos extraídos diretamente dos claims do token:
        usuario_id   — claim "id"   (PK em sap.dgeo.usuario)
        usuario_uuid — claim "uuid" (identificador público)
        administrador — claim "administrador" (perfil de acesso)
    """

    usuario_id: int
    usuario_uuid: str
    administrador: bool

    @property
    def eh_admin(self) -> bool:
        return self.administrador


@dataclass(frozen=True)
class DadosUsuario:
    """Dados completos do usuário obtidos do servico_autenticacao."""

    uuid: str
    login: str
    nome: str
    nome_guerra: str | None = None
    tipo_posto_grad_id: int | None = None
    tipo_turno_id: int | None = None


@dataclass(frozen=True)
class ResultadoAutenticacao:
    """Resultado de uma autenticação bem-sucedida."""

    token: str
    uuid: str
    administrador: bool


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------


class AuthProvider(ABC):
    """Interface para provedores de autenticação.

    Implementações:
        - RealAuthProvider: integração com servico_autenticacao
        - MockAuthProvider: mock para testes CI
    """

    @abstractmethod
    def verificar_disponibilidade(self) -> bool:
        """Verifica se o serviço de autenticação está operacional.

        Returns:
            True se o serviço responde corretamente.

        Raises:
            ServicoIndisponivel: se não conseguir conectar.
        """
        ...

    @abstractmethod
    def autenticar_usuario(self, usuario: str, senha: str, aplicacao: str = "sap") -> ResultadoAutenticacao:
        """Autentica usuário no servico_autenticacao.

        Args:
            usuario: login do usuário
            senha: senha do usuário
            aplicacao: identificador da aplicação cliente (default: 'sap')
                       O capacidade_produtiva compartilha a mesma base de
                       usuários do SAP, então usamos 'sap' como aplicação.

        Returns:
            ResultadoAutenticacao com token, uuid e flag administrador.

        Raises:
            CredenciaisInvalidas: se usuário/senha incorretos.
            ServicoIndisponivel: se serviço inacessível.
        """
        ...

    @abstractmethod
    def validar_token(self, token: str) -> UsuarioAutenticado:
        """Valida assinatura do token e extrai contexto do usuário.

        Args:
            token: JWT a ser validado (com ou sem prefixo Bearer)

        Returns:
            UsuarioAutenticado com dados extraídos dos claims.

        Raises:
            TokenInvalido: se token ausente, expirado ou inválido.
        """
        ...

    @abstractmethod
    def obter_dados_usuario(self, token: str, uuid: str) -> DadosUsuario:
        """Busca dados completos do usuário autenticado.

        Args:
            token: JWT válido para autorização
            uuid: identificador do usuário

        Returns:
            DadosUsuario com informações do perfil.

        Raises:
            TokenInvalido: se token inválido.
            ServicoIndisponivel: se serviço inacessível.
        """
        ...


# ---------------------------------------------------------------------------
# Implementação Real (Produção)
# ---------------------------------------------------------------------------


class RealAuthProvider(AuthProvider):
    """Provedor de autenticação real — integra com servico_autenticacao.

    Responsabilidades:
        - Validar credenciais via POST /api/login
        - Validar tokens JWT localmente (assinatura)
        - Buscar dados de usuário via GET /api/usuarios/:uuid

    O JWT_SECRET deve ser o mesmo utilizado pelo SAP para que
    tokens emitidos pelo SAP sejam válidos no Capacidade Produtiva.
    """

    def __init__(self, auth_url: str, jwt_secret: str) -> None:
        """Inicializa o provedor.

        Args:
            auth_url: URL base do servico_autenticacao (ex: http://localhost:3010)
            jwt_secret: chave secreta para validação de tokens (compartilhada com SAP)
        """
        self._auth_url = auth_url.rstrip("/")
        self._jwt_secret = jwt_secret

    def verificar_disponibilidade(self) -> bool:
        from cp.infrastructure.http_client import http_get

        try:
            status, data = http_get(f"{self._auth_url}/api")
            if status != 200:
                raise ServicoIndisponivel(f"Serviço retornou HTTP {status}")
            if data.get("message") != "Serviço de autenticação operacional":
                raise ServicoIndisponivel(f"Resposta inesperada: {data}")
            return True
        except OSError as exc:
            raise ServicoIndisponivel(f"Erro de conexão: {exc}") from exc

    def autenticar_usuario(self, usuario: str, senha: str, aplicacao: str = "sap") -> ResultadoAutenticacao:
        from cp.infrastructure.http_client import http_post

        endpoint = f"{self._auth_url}/api/login"
        payload = {"usuario": usuario, "senha": senha, "aplicacao": aplicacao}

        try:
            status, data = http_post(endpoint, payload)
        except OSError as exc:
            raise ServicoIndisponivel(f"Erro ao conectar: {exc}") from exc

        if status != 201:
            msg = data.get("message", "Credenciais inválidas")
            raise CredenciaisInvalidas(msg)

        if not data.get("success"):
            raise CredenciaisInvalidas("Autenticação falhou")

        dados = data.get("dados", {})
        token = dados.get("token")
        uuid = dados.get("uuid")
        administrador = dados.get("administrador", False)

        if not token or not uuid:
            raise ServicoIndisponivel("Resposta incompleta do serviço")

        return ResultadoAutenticacao(
            token=token,
            uuid=uuid,
            administrador=administrador,
        )

    def validar_token(self, token: str) -> UsuarioAutenticado:
        # Remove prefixo Bearer se presente
        token = _extrair_token_bruto(token)

        try:
            payload = jwt.decode(token, self._jwt_secret, algorithms=[_ALGORITMO])
        except jwt.exceptions.ExpiredSignatureError:
            raise TokenInvalido("Token expirado.")
        except jwt.exceptions.InvalidTokenError as exc:
            _logger.debug("Token inválido: %s", exc)
            raise TokenInvalido("Token inválido.") from exc

        try:
            usuario_id = int(payload["id"])
            usuario_uuid = str(payload["uuid"])
            administrador = bool(payload.get("administrador", False))
        except (KeyError, ValueError, TypeError) as exc:
            raise TokenInvalido("Claims obrigatórios ausentes no token.") from exc

        return UsuarioAutenticado(
            usuario_id=usuario_id,
            usuario_uuid=usuario_uuid,
            administrador=administrador,
        )

    def obter_dados_usuario(self, token: str, uuid: str) -> DadosUsuario:
        from cp.infrastructure.http_client import http_get

        endpoint = f"{self._auth_url}/api/usuarios/{uuid}"
        headers = {"Authorization": f"Bearer {_extrair_token_bruto(token)}"}

        try:
            status, data = http_get(endpoint, headers=headers)
        except OSError as exc:
            raise ServicoIndisponivel(f"Erro ao conectar: {exc}") from exc

        if status == 401:
            raise TokenInvalido("Token inválido ou expirado")
        if status != 200:
            raise ServicoIndisponivel(f"Erro ao buscar usuário: HTTP {status}")

        dados = data.get("dados", {})
        return DadosUsuario(
            uuid=dados.get("uuid", uuid),
            login=dados.get("login", ""),
            nome=dados.get("nome", ""),
            nome_guerra=dados.get("nome_guerra"),
            tipo_posto_grad_id=dados.get("tipo_posto_grad_id"),
            tipo_turno_id=dados.get("tipo_turno_id"),
        )


# ---------------------------------------------------------------------------
# Implementação Mock (Testes CI)
# ---------------------------------------------------------------------------


# Usuários pré-definidos para testes
_MOCK_USERS: dict[str, dict[str, str | int | bool]] = {
    "admin": {
        "id": 1,
        "uuid": "00000000-0000-0000-0000-000000000001",
        "login": "admin",
        "nome": "Administrador Teste",
        "senha": "admin123",
        "administrador": True,
    },
    "operador": {
        "id": 2,
        "uuid": "00000000-0000-0000-0000-000000000002",
        "login": "operador",
        "nome": "Operador Teste",
        "senha": "operador123",
        "administrador": False,
    },
}


class MockAuthProvider(AuthProvider):
    """Provedor de autenticação mock para testes CI.

    Características:
        - Não faz chamadas de rede
        - Aceita usuários pré-definidos em _MOCK_USERS
        - Valida tokens com JWT_SECRET fixo
        - Totalmente determinístico e reproduzível
    """

    def __init__(self, jwt_secret: str = "test-secret-for-ci") -> None:
        self._jwt_secret = jwt_secret

    def verificar_disponibilidade(self) -> bool:
        return True  # Mock sempre disponível

    def autenticar_usuario(self, usuario: str, senha: str, aplicacao: str = "sap") -> ResultadoAutenticacao:
        user = _MOCK_USERS.get(usuario)
        if not user or user["senha"] != senha:
            raise CredenciaisInvalidas("Usuário ou senha inválida")

        # Gera token mock válido por 5 horas
        payload = {
            "id": user["id"],
            "uuid": user["uuid"],
            "administrador": user["administrador"],
            "exp": int(time.time()) + 18_000,
        }
        token = jwt.encode(payload, self._jwt_secret, algorithm=_ALGORITMO)

        return ResultadoAutenticacao(
            token=token,
            uuid=str(user["uuid"]),
            administrador=bool(user["administrador"]),
        )

    def validar_token(self, token: str) -> UsuarioAutenticado:
        token = _extrair_token_bruto(token)

        try:
            payload = jwt.decode(token, self._jwt_secret, algorithms=[_ALGORITMO])
        except jwt.exceptions.ExpiredSignatureError:
            raise TokenInvalido("Token expirado.")
        except jwt.exceptions.InvalidTokenError as exc:
            raise TokenInvalido("Token inválido.") from exc

        return UsuarioAutenticado(
            usuario_id=int(payload["id"]),
            usuario_uuid=str(payload["uuid"]),
            administrador=bool(payload.get("administrador", False)),
        )

    def obter_dados_usuario(self, token: str, uuid: str) -> DadosUsuario:
        # Valida token primeiro
        self.validar_token(token)

        # Busca nos usuários mock
        for user in _MOCK_USERS.values():
            if user["uuid"] == uuid:
                return DadosUsuario(
                    uuid=str(user["uuid"]),
                    login=str(user["login"]),
                    nome=str(user["nome"]),
                )

        raise TokenInvalido(f"Usuário {uuid} não encontrado")


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def criar_auth_provider(settings: Settings) -> AuthProvider:
    """Cria o provedor de autenticação apropriado baseado nas settings.

    Em modo de teste (TESTING_MODE=true ou ENVIRONMENT=test):
        Retorna MockAuthProvider

    Em produção:
        Retorna RealAuthProvider configurado com AUTH_URL e JWT_SECRET

    Args:
        settings: configurações da aplicação

    Returns:
        AuthProvider configurado para o ambiente.
    """
    is_testing = settings.environment.lower() == "test" or getattr(settings, "testing_mode", False)

    if is_testing:
        _logger.info("Usando MockAuthProvider (ambiente de teste)")
        return MockAuthProvider(jwt_secret=settings.jwt_secret)

    if not settings.auth_url:
        raise ValueError("AUTH_URL deve ser definido em produção")

    _logger.info("Usando RealAuthProvider (auth_url=%s)", settings.auth_url)
    return RealAuthProvider(
        auth_url=settings.auth_url,
        jwt_secret=settings.jwt_secret,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extrair_token_bruto(authorization: str | None) -> str:
    """Extrai o token bruto do header Authorization.

    Aceita:
        Authorization: eyJ...
        Authorization: Bearer eyJ...

    Raises:
        TokenInvalido: se o header estiver ausente ou vazio.
    """
    if not authorization:
        raise TokenInvalido("Header Authorization ausente.")
    authorization = authorization.strip()
    if not authorization:
        raise TokenInvalido("Header Authorization vazio.")

    partes = authorization.split(" ", 1)
    if len(partes) == 2 and partes[0].lower() == "bearer":
        return partes[1].strip()
    return partes[0].strip()
