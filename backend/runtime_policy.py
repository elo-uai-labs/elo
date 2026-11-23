"""Explicit local-runtime guardrails; not a corporate deployment approval."""
import os


def validate_runtime(access_service):
    environment = os.getenv('ELO_ENV', 'local').strip().lower()
    if environment not in {'local', 'test'}:
        raise ValueError('ELO_ENV aceita somente local ou test. Implantação corporativa/produção ainda não autorizada nesta versão.')
    require_auth = os.getenv('ELO_REQUIRE_AUTH', '0').strip()
    if require_auth not in {'0', '1'}:
        raise ValueError('ELO_REQUIRE_AUTH deve ser 0 ou 1.')
    if require_auth == '1' and access_service is None:
        raise ValueError('ELO_REQUIRE_AUTH=1 exige ELO_AUTH_USERS_FILE válido; modo demonstrativo bloqueado.')
