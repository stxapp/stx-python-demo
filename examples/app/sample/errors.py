"""One clear page for each way STX can say no.

``describe()`` turns an SDK exception into what the error page shows. The
order of the checks matters: the specific classes derive from the general
ones (every OAuth error is an ``STXAuthenticationException``, every 403 an
``STXForbiddenException``).
"""

from dataclasses import dataclass
from typing import Optional

import stx
from stx import oauth

DOCS = "https://docs.stxapp.io"


@dataclass(frozen=True)
class ErrorPage:
    status: int
    title: str
    message: str
    action_label: Optional[str] = None
    action_url: Optional[str] = None
    code: Optional[str] = None


def describe(exc: Exception, *, connect_url: str, return_url: str) -> ErrorPage:
    """What to show for ``exc``. ``connect_url`` starts a new connection;
    ``return_url`` is where STX's terms page sends the member back to."""

    # Raised from member calls: the connection ended or needs the member.
    if isinstance(exc, oauth.STXGrantRevokedException):
        return ErrorPage(
            401,
            "Your STX account is no longer connected",
            "You disconnected this app in STX, or the connection expired. The app has deleted its tokens. "
            "Connect your STX account again to carry on.",
            "Connect your STX account",
            connect_url,
            "grant_revoked",
        )
    if isinstance(exc, oauth.STXAccountPendingException):
        return ErrorPage(
            403,
            "Your STX account is still being verified",
            "STX is still checking your identity, so it cannot connect your account yet. "
            "Try again once STX has approved it.",
            "What this means",
            f"{DOCS}/oauth/members-being-verified/",
            "account_pending",
        )
    if isinstance(exc, oauth.STXTermsNotAcceptedException):
        return ErrorPage(
            403,
            "You did not accept the STX terms",
            "STX connects your account only after you agree to its current terms. Nothing was connected.",
            "Try again",
            connect_url,
            "terms_required",
        )
    if isinstance(exc, oauth.STXAccessDeniedException):
        return ErrorPage(
            403,
            "Your STX account was not connected",
            "You chose not to connect, or STX could not connect this account. Nothing was shared with this app.",
            "Try again",
            connect_url,
            "access_denied",
        )
    if isinstance(exc, oauth.STXOAuthException):
        return ErrorPage(
            400,
            "Connecting your STX account did not finish",
            f"STX answered {exc.error}"
            + (f": {exc.error_description}" if exc.error_description else ".")
            + " Start again from this app.",
            "Start again",
            connect_url,
            exc.error,
        )

    # Raised from member calls that are refused, while the connection stands.
    if isinstance(exc, stx.STXTermsRequiredException):
        url = oauth.terms_url_with_return(exc.terms_url, return_url) if exc.terms_url else None
        return ErrorPage(
            403,
            "Accept the new STX terms to place orders",
            "STX has new terms. You can still see your account and cancel orders, but STX places no new orders "
            "until you accept them. You accept on STX's own page, signed in to your account, and come straight back.",
            "Review the STX terms" if url else None,
            url,
            "terms_required",
        )
    if isinstance(exc, stx.STXIpNotAllowedException):
        return ErrorPage(
            403,
            "This server is not on the app's IP allow-list",
            "STX takes orders from an app only from the addresses listed for it. Reads work from anywhere. "
            "Add this server's public address to the app in STX Apps.",
            "About the IP allow-list",
            f"{DOCS}/oauth/ip-allow-list/",
            "ip_not_allowed",
        )
    if isinstance(exc, stx.STXInsufficientScopeException):
        needed = " ".join(exc.required_scopes) or "a scope you did not allow"
        return ErrorPage(
            403,
            "This needs more access",
            f"This action needs {needed}. Connect again and allow it.",
            "Connect again",
            connect_url,
            "insufficient_scope",
        )

    # The exchange does not offer the feature at all.
    if isinstance(exc, stx.STXNotAvailableError):
        return ErrorPage(
            501,
            "Not available on this exchange",
            f"{exc} This app needs the '{exc.feature}' feature. Point it at an exchange that offers it "
            "(US demo does) with STX_REGION and STX_ENV.",
            "What each exchange offers",
            f"{DOCS}/sdks/python/capabilities/",
            "not_available",
        )

    # The exchange looked at the order and said no: a closed market, a bad
    # price, not enough balance. The reason is STX's own words.
    if isinstance(exc, (stx.STXRejectedException, stx.STXValidationException)):
        return ErrorPage(
            422,
            "STX did not accept the order",
            str(exc),
            "Back to your dashboard",
            "/dashboard",
            "rejected",
        )

    if isinstance(exc, stx.STXException):
        return ErrorPage(502, "STX refused the request", str(exc), code=type(exc).__name__)
    return ErrorPage(500, "Something went wrong", str(exc) or type(exc).__name__)
