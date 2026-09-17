"""Adaptador de Integração BaaS Pix (Efí Pay / PSP Banco Central).

Suporta:
- Autenticação mTLS através de certificado digital .pem (RFC 5246).
- Gerenciamento de ciclo de vida de OAuth 2.0 Bearer Token com renovação automática.
- Envio imediato de Pix para chave (CPF, CNPJ, Email, Telefone, EVP) via PUT /v2/gn/pix/{idEnvio}.
- Consulta de saldo disponível na conta jurídica da instituição via GET /v2/gn/saldo.
- Modo Sandbox / Mock para testes e ambientes de desenvolvimento local sem certificados reais.
"""

from __future__ import annotations

import base64
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

import httpx

logger = logging.getLogger("finance.baas")


@dataclass
class BaasPayoutResult:
    """Resultado estruturado da tentativa de envio PIX via BaaS."""
    success: bool
    tx_id: str
    e2e_id: Optional[str] = None
    raw_response: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    is_transient_error: bool = False  # Se True, elegível para retry assíncrono no Celery


class EfiBaasError(Exception):
    """Erro genérico de comunicação ou rejeição da Efí Pay."""
    def __init__(self, message: str, raw_response: Optional[Dict[str, Any]] = None, is_transient: bool = False):
        super().__init__(message)
        self.raw_response = raw_response or {}
        self.is_transient = is_transient


class EfiBaasClient:
    """Cliente HTTP com suporte a mTLS e OAuth 2.0 para a API Pix da Efí Pay."""

    PROD_URL = "https://pix.sejaefi.com.br"
    HOMOLOG_URL = "https://pix-h.sejaefi.com.br"

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        cert_path: Optional[str] = None,
        pix_key: Optional[str] = None,
        sandbox: Optional[bool] = None,
        mock_mode: Optional[bool] = None,
    ):
        self.client_id = client_id or os.getenv("EFI_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("EFI_CLIENT_SECRET", "")
        self.cert_path = cert_path or os.getenv("EFI_CERT_PATH", "")
        self.operator_pix_key = pix_key or os.getenv("EFI_OPERATOR_PIX_KEY", "")

        # Sandbox flag
        env_sandbox = os.getenv("EFI_SANDBOX", "true").lower() in ("true", "1", "t")
        self.sandbox = sandbox if sandbox is not None else env_sandbox

        # Mock mode se ativado explicitamente ou se não houver certificado configurado
        env_mock = os.getenv("EFI_MOCK_MODE", "").lower() in ("true", "1", "t")
        if mock_mode is not None:
            self.mock_mode = mock_mode
        elif env_mock:
            self.mock_mode = True
        else:
            # Se não tiver cert_path existente no disco, ativa modo mock seguro
            self.mock_mode = not (self.cert_path and os.path.isfile(self.cert_path))

        self.base_url = self.HOMOLOG_URL if self.sandbox else self.PROD_URL
        self._cached_token: Optional[str] = None
        self._token_expires_at: float = 0.0

    @staticmethod
    def sanitize_pix_key(key: str, key_type: str) -> str:
        """Sanitiza e valida o formato da chave PIX de acordo com as regras do Bacen."""
        cleaned = key.strip()
        k_type = key_type.upper()

        if k_type in ("CPF", "CNPJ"):
            return re.sub(r"\D", "", cleaned)
        elif k_type == "PHONE":
            digits = re.sub(r"\D", "", cleaned)
            if not digits.startswith("55"):
                digits = f"55{digits}"
            return f"+{digits}"
        elif k_type == "EMAIL":
            return cleaned.lower()
        elif k_type == "EVP":
            return cleaned.lower()
        return cleaned

    def _get_http_client(self) -> httpx.Client:
        """Instancia o cliente HTTP com suporte a mTLS se certificado existir."""
        cert_arg = self.cert_path if (self.cert_path and os.path.isfile(self.cert_path)) else None
        return httpx.Client(
            base_url=self.base_url,
            cert=cert_arg,
            timeout=15.0,
            verify=True,
        )

    def get_oauth_token(self, force_refresh: bool = False) -> str:
        """Obtém ou renova o Bearer Token OAuth 2.0."""
        now = time.time()
        if not force_refresh and self._cached_token and now < (self._token_expires_at - 60):
            return self._cached_token

        if self.mock_mode:
            self._cached_token = f"mock_bearer_token_{uuid.uuid4().hex[:12]}"
            self._token_expires_at = now + 3600
            return self._cached_token

        if not self.client_id or not self.client_secret:
            raise EfiBaasError("Credenciais Efí Pay ausentes (EFI_CLIENT_ID ou EFI_CLIENT_SECRET).")

        basic_auth = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        headers = {
            "Authorization": f"Basic {basic_auth}",
            "Content-Type": "application/json",
        }
        body = {"grant_type": "client_credentials"}

        try:
            with self._get_http_client() as client:
                res = client.post("/oauth/token", headers=headers, json=body)
                if res.status_code != 200:
                    logger.error("Falha ao obter token OAuth Efí: %s - %s", res.status_code, res.text)
                    raise EfiBaasError(
                        f"Falha na autenticação OAuth Efí: HTTP {res.status_code}",
                        raw_response={"status_code": res.status_code, "body": res.text},
                        is_transient=(res.status_code >= 500 or res.status_code == 429),
                    )
                data = res.json()
                access_token = data.get("access_token")
                expires_in = data.get("expires_in", 3600)
                if not access_token:
                    raise EfiBaasError("Resposta OAuth Efí inválida: 'access_token' não encontrado.")

                self._cached_token = access_token
                self._token_expires_at = now + float(expires_in)
                return access_token
        except httpx.RequestError as exc:
            logger.exception("Erro de rede ao conectar à Efí Pay OAuth")
            raise EfiBaasError(f"Erro de conexão com BaaS OAuth: {str(exc)}", is_transient=True) from exc

    def send_pix_to_key(
        self,
        amount_cents: int,
        destination_key: str,
        destination_key_type: str,
        correlation_id: Optional[str] = None,
        source_key: Optional[str] = None,
    ) -> BaasPayoutResult:
        """Executa transferência PIX imediata via PUT /v2/gn/pix/{idEnvio}."""
        if amount_cents <= 0:
            return BaasPayoutResult(
                success=False,
                tx_id="",
                error_message="Valor de saque inválido (menor ou igual a zero).",
            )

        sanitized_key = self.sanitize_pix_key(destination_key, destination_key_type)
        payer_key = source_key or self.operator_pix_key or "expressoneves@pix.com.br"
        id_envio = correlation_id or str(uuid.uuid4()).replace("-", "")[:32]
        amount_reais_str = f"{amount_cents / 100:.2f}"

        # Se estiver em modo mock (testes locais ou CI)
        if self.mock_mode:
            logger.info(
                "[MOCK BAAS] PIX simulado enviado com sucesso: R$ %s para chave %s (%s)",
                amount_reais_str, sanitized_key, destination_key_type
            )
            mock_e2e = f"E00038166{time.strftime('%Y%m%d%H%M')}{uuid.uuid4().hex[:11]}"
            return BaasPayoutResult(
                success=True,
                tx_id=id_envio,
                e2e_id=mock_e2e,
                raw_response={
                    "idEnvio": id_envio,
                    "e2eId": mock_e2e,
                    "valor": amount_reais_str,
                    "status": "REALIZADO",
                    "horario": {"solicitacao": time.strftime("%Y-%m-%dT%H:%M:%SZ")},
                    "favorecido": {"chave": sanitized_key},
                },
            )

        payload = {
            "valor": amount_reais_str,
            "pagador": {
                "chave": payer_key,
            },
            "favorecido": {
                "chave": sanitized_key,
            },
        }

        try:
            token = self.get_oauth_token()
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            with self._get_http_client() as client:
                res = client.put(f"/v2/gn/pix/{id_envio}", headers=headers, json=payload)
                status_code = res.status_code

                try:
                    res_data = res.json()
                except Exception:
                    res_data = {"raw_text": res.text}

                if status_code in (200, 201):
                    # Liquidação ou aceitação SPI
                    e2e_id = res_data.get("e2eId") or res_data.get("endToEndId")
                    return BaasPayoutResult(
                        success=True,
                        tx_id=id_envio,
                        e2e_id=e2e_id,
                        raw_response=res_data,
                    )

                # Tratamento de erros HTTP 4xx ou 5xx
                is_transient = status_code >= 500 or status_code == 429
                error_desc = res_data.get("mensagem") or res_data.get("error_description") or res_data.get("detail") or str(res_data)
                logger.error("Rejeição da Efí no envio PIX: HTTP %s - %s", status_code, error_desc)

                return BaasPayoutResult(
                    success=False,
                    tx_id=id_envio,
                    error_message=f"Efí HTTP {status_code}: {error_desc}",
                    raw_response=res_data,
                    is_transient_error=is_transient,
                )

        except httpx.RequestError as exc:
            logger.exception("Falha de conexão de rede durante transferência PIX Efí")
            return BaasPayoutResult(
                success=False,
                tx_id=id_envio,
                error_message=f"Timeout ou falha de rede BaaS: {str(exc)}",
                is_transient_error=True,
            )

    def get_account_balance(self) -> Dict[str, Any]:
        """Consulta o saldo disponível na conta jurídica da Efí Pay."""
        if self.mock_mode:
            return {
                "saldo": 25480.50,
                "saldo_cents": 2548050,
                "bloqueado": 0.0,
                "mock": True,
            }

        try:
            token = self.get_oauth_token()
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            with self._get_http_client() as client:
                res = client.get("/v2/gn/saldo", headers=headers)
                if res.status_code != 200:
                    raise EfiBaasError(
                        f"Erro ao consultar saldo Efí: HTTP {res.status_code}",
                        raw_response={"status_code": res.status_code, "body": res.text},
                        is_transient=(res.status_code >= 500),
                    )
                data = res.json()
                saldo_float = float(data.get("saldo", 0.0))
                saldo_cents = round(saldo_float * 100)
                return {
                    "saldo": saldo_float,
                    "saldo_cents": saldo_cents,
                    "bloqueado": float(data.get("bloqueado", 0.0)),
                    "mock": False,
                }
        except httpx.RequestError as exc:
            logger.exception("Erro de rede ao consultar saldo Efí")
            raise EfiBaasError(f"Erro de conexão com BaaS Saldo: {str(exc)}", is_transient=True) from exc
