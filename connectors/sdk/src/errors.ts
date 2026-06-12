export class ConnectorError extends Error {
  public readonly code: string;

  public readonly causeError?: Error;

  constructor(message: string, code = 'CONNECTOR_ERROR', cause?: Error) {
    super(message);
    this.name = 'ConnectorError';
    this.code = code;
    this.causeError = cause;
  }
}

export class RecoverableConnectorError extends ConnectorError {
  constructor(message: string, code = 'CONNECTOR_RECOVERABLE', cause?: Error) {
    super(message, code, cause);
    this.name = 'RecoverableConnectorError';
  }
}

export class FatalConnectorError extends ConnectorError {
  constructor(message: string, code = 'CONNECTOR_FATAL', cause?: Error) {
    super(message, code, cause);
    this.name = 'FatalConnectorError';
  }
}
