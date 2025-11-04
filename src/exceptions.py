"""
Custom exceptions for MAS-Eval microservice
"""


class MASEvalException(Exception):
    """Base exception for MAS-Eval microservice."""
    pass


class AgentExecutionError(MASEvalException):
    """Raised when an agent fails to execute properly."""
    pass


class InvalidInputDataError(MASEvalException):
    """Raised when input data validation fails."""
    pass


class GraphExecutionError(MASEvalException):
    """Raised when LangGraph execution fails."""
    pass

