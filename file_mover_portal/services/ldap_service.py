from __future__ import annotations

import hmac
import ssl
from urllib.parse import urlparse

from ldap3 import BASE, Connection, NONE, Server, Tls
from ldap3.core.exceptions import LDAPException
from ldap3.utils.dn import escape_rdn


class LDAPAuthenticationError(Exception):
    pass


class LDAPService:
    AD_MATCHING_RULE_IN_CHAIN = "1.2.840.113556.1.4.1941"

    def __init__(self, config) -> None:
        self.enabled = config["LDAP_ENABLED"]
        self.server_uri = config["LDAP_SERVER"]
        self.use_ssl = config["LDAP_USE_SSL"]
        self.ca_cert_file = config["LDAP_CA_CERT_FILE"] or None
        self.connect_timeout = config["LDAP_CONNECT_TIMEOUT"]
        self.user_dn_template = config["LDAP_USER_DN_TEMPLATE"]
        self.bind_dn = config["LDAP_BIND_DN"]
        self.bind_password = config["LDAP_BIND_PASSWORD"]
        self.base_dn = config["LDAP_BASE_DN"]
        self.user_filter = config["LDAP_USER_FILTER"]
        self.required_group_dns = tuple(config["LDAP_GROUPS_REQUIRED"])
        self.required_group_dns_normalized = {group.casefold() for group in self.required_group_dns}
        self.group_match_mode = config["LDAP_GROUP_MATCH_MODE"]
        self.nested_groups_enabled = config["LDAP_NESTED_GROUPS_ENABLED"]
        self.group_attribute = config["LDAP_GROUP_ATTRIBUTE"]
        self.email_attribute = config["LDAP_EMAIL_ATTRIBUTE"]
        self.email_template = config["LDAP_EMAIL_TEMPLATE"]
        self.dev_username = config["DEV_USERNAME"]
        self.dev_password = config["DEV_PASSWORD"]
        self.dev_email = config["DEV_EMAIL"]

        if self.enabled and not self.use_ssl:
            raise RuntimeError("LDAP authentication requires LDAPS/TLS")
        if self.enabled and self.required_group_dns and (
            not self.bind_dn or not self.bind_password or not self.base_dn
        ):
            raise RuntimeError("LDAP group authorization requires bind credentials and LDAP_BASE_DN")
        if not self.enabled and (not self.dev_username or len(self.dev_password) < 12):
            raise RuntimeError("Development credentials must be explicitly set; password must be at least 12 characters")

    def _server(self) -> Server:
        parsed = urlparse(self.server_uri if "://" in self.server_uri else f"ldaps://{self.server_uri}")
        if parsed.scheme.lower() != "ldaps":
            raise RuntimeError("LDAP_SERVER must use the ldaps:// scheme")
        host = parsed.hostname
        if not host:
            raise RuntimeError("LDAP_SERVER is invalid")
        port = parsed.port or 636
        tls = Tls(validate=ssl.CERT_REQUIRED, ca_certs_file=self.ca_cert_file, version=ssl.PROTOCOL_TLS_CLIENT)
        return Server(host, port=port, get_info=NONE, connect_timeout=self.connect_timeout, use_ssl=True, tls=tls)

    @staticmethod
    def _escape_filter(value: str) -> str:
        return (
            value.replace("\\", r"\5c")
            .replace("*", r"\2a")
            .replace("(", r"\28")
            .replace(")", r"\29")
            .replace("\x00", r"\00")
        )

    def _connection(self, *, user: str, password: str) -> Connection:
        return Connection(
            self._server(),
            user=user,
            password=password,
            auto_bind=True,
            auto_referrals=False,
            receive_timeout=self.connect_timeout,
            raise_exceptions=True,
        )

    def authenticate(self, username: str, password: str) -> str:
        if not self.enabled:
            if hmac.compare_digest(username, self.dev_username) and hmac.compare_digest(password, self.dev_password):
                return self.dev_email
            raise LDAPAuthenticationError("Credentials rejected")

        if self.user_dn_template:
            user_dn = self.user_dn_template.format(username=escape_rdn(username))
            try:
                with self._connection(user=user_dn, password=password):
                    pass
            except LDAPException as exc:
                raise LDAPAuthenticationError("LDAP authentication failed") from exc
            identity = self._lookup_identity(username)
            return identity["email"] or self._email_from_template(username)

        return self._search_then_bind(username, password)

    def lookup_authorized_email(self, username: str) -> str:
        """Resolve email again with the service account; do not store PII in the client cookie."""
        if not self.enabled:
            if hmac.compare_digest(username, self.dev_username):
                return self.dev_email
            raise LDAPAuthenticationError("LDAP authentication failed")
        identity = self._lookup_identity(username)
        return str(identity.get("email", "")) or self._email_from_template(username)

    def _email_from_template(self, username: str) -> str:
        return self.email_template.format(username=username) if self.email_template else ""

    def _is_directly_authorized(self, groups: set[str]) -> bool:
        if not self.required_group_dns_normalized:
            return True
        matched = self.required_group_dns_normalized.intersection(groups)
        if self.group_match_mode == "ALL":
            return self.required_group_dns_normalized.issubset(groups)
        return bool(matched)

    def _is_nested_authorized(self, conn: Connection, user_dn: str) -> bool:
        """Use Active Directory's recursive memberOf matching rule for nested groups."""
        if not self.required_group_dns:
            return True

        expressions = [
            f"({self.group_attribute}:{self.AD_MATCHING_RULE_IN_CHAIN}:={self._escape_filter(group_dn)})"
            for group_dn in self.required_group_dns
        ]
        if self.group_match_mode == "ALL":
            authorization_filter = f"(&{''.join(expressions)})"
        else:
            authorization_filter = expressions[0] if len(expressions) == 1 else f"(|{''.join(expressions)})"

        conn.search(
            search_base=user_dn,
            search_filter=authorization_filter,
            search_scope=BASE,
            attributes=[],
            size_limit=1,
        )
        return len(conn.entries) == 1

    def _lookup_identity(self, username: str) -> dict:
        if not self.bind_dn or not self.bind_password or not self.base_dn:
            return {"email": "", "groups": set()}
        search_filter = self.user_filter.format(username=self._escape_filter(username))
        try:
            with self._connection(user=self.bind_dn, password=self.bind_password) as conn:
                attributes = list(dict.fromkeys([self.group_attribute, self.email_attribute]))
                conn.search(self.base_dn, search_filter, attributes=attributes, size_limit=2)
                if len(conn.entries) != 1:
                    raise LDAPAuthenticationError("LDAP authentication failed")

                entry = conn.entries[0]
                groups = (
                    {str(value).casefold() for value in entry[self.group_attribute].values}
                    if self.group_attribute in entry
                    else set()
                )

                if self.required_group_dns:
                    authorized = (
                        self._is_nested_authorized(conn, entry.entry_dn)
                        if self.nested_groups_enabled
                        else self._is_directly_authorized(groups)
                    )
                    if not authorized:
                        raise LDAPAuthenticationError("LDAP authentication failed")

                values = entry[self.email_attribute].values if self.email_attribute in entry else []
                return {
                    "email": str(values[0]).strip() if values else "",
                    "groups": groups,
                    "dn": entry.entry_dn,
                }
        except LDAPAuthenticationError:
            raise
        except LDAPException as exc:
            raise LDAPAuthenticationError("LDAP authentication failed") from exc

    def _search_then_bind(self, username: str, password: str) -> str:
        if not self.bind_dn or not self.bind_password or not self.base_dn:
            raise LDAPAuthenticationError("LDAP configuration is incomplete")
        identity = self._lookup_identity(username)
        user_dn = str(identity.get("dn", ""))
        if not user_dn:
            raise LDAPAuthenticationError("LDAP authentication failed")
        try:
            with self._connection(user=user_dn, password=password):
                pass
            return str(identity.get("email", "")) or self._email_from_template(username)
        except LDAPException as exc:
            raise LDAPAuthenticationError("LDAP authentication failed") from exc
