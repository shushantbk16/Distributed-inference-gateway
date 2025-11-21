"""Custom exception classes for the inference gateway."""


class InferenceGatewayError(Exception):
    """Base exception for all gateway errors."""
    pass


class ProviderError(InferenceGatewayError):
    """Exception raised when an LLM provider fails."""
    
    def __init__(self, provider: str, message: str, original_error: Exception = None):
        self.provider = provider
        self.original_error = original_error
        super().__init__(f"Provider '{provider}' error: {message}")


class SandboxError(InferenceGatewayError):
    """Exception raised when sandbox execution fails."""
    
    def __init__(self, message: str, exit_code: int = None, stderr: str = None):
        self.exit_code = exit_code
        self.stderr = stderr
        super().__init__(message)


class VerificationError(InferenceGatewayError):
    """Exception raised when verification fails."""
    pass


class ConfigurationError(InferenceGatewayError):
    """Exception raised for configuration issues."""
    pass


class CodeExtractionError(InferenceGatewayError):
    """Exception raised when code extraction fails."""
    pass


class TimeoutError(InferenceGatewayError):
    """Exception raised when operations timeout."""
    pass
