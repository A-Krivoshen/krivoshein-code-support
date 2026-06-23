class MaxApiError(Exception):
    """Base error for MAX API client failures."""


class MaxApiRequestError(MaxApiError):
    """HTTP transport or non-success API error."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code


class MaxApiResponseError(MaxApiError):
    """Unexpected response structure from MAX API."""