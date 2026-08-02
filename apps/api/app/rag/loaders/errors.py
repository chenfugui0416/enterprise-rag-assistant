"""Public parsing errors with messages safe to return from an API later."""


class DocumentParseError(ValueError):
    """Base class for expected document parsing failures."""


class UnsupportedDocumentTypeError(DocumentParseError):
    """The file extension does not map to an enabled parser."""


class EmptyDocumentError(DocumentParseError):
    """The document is valid but contains no extractable text."""


class EncryptedDocumentError(DocumentParseError):
    """The parser cannot read a password-protected document."""


class DocumentTooLargeError(DocumentParseError):
    """The source exceeds the configured byte limit."""
