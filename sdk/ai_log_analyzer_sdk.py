import requests
import traceback
import logging


class LogAnalyzerSDK:
    def __init__(self, api_url, api_key):
        self.api_url = api_url
        self.api_key = api_key

    def _send_log(self, message):
        try:
            print("SENDING LOG:", message)  # ← add this line
            requests.post(
                f"{self.api_url}/api/ingest",
                json={"logs": [message]},
                headers={"X-API-Key": self.api_key}
            )
        except Exception as e:
            print("SDK failed to send log:", e)

    def capture_exception(self, error):
        error_message = f"ERROR {type(error).__name__}: {str(error)}"
        self._send_log(error_message)

    def capture_message(self, message):
        log_message = f"INFO {message}"
        self._send_log(log_message)

    def setup_auto_capture(self):
        sdk_self = self

        class LoggingHandler(logging.Handler):
            def __init__(self):
                super().__init__()
                self._is_handling = False

            def emit(self, record):
                if self._is_handling:
                    return
                if record.levelno < logging.WARNING:
                    return
                self._is_handling = True
                try:
                    log_entry = self.format(record)
                    if record.levelno >= logging.ERROR:
                        sdk_self._send_log(f"ERROR {log_entry}")
                    elif record.levelno >= logging.WARNING:
                        sdk_self._send_log(f"WARN {log_entry}")
                finally:
                    self._is_handling = False

        handler = LoggingHandler()
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.DEBUG)

    def setup_auto_capture2(self):
        class LoggingHandler(logging.Handler):
            def emit(inner_self, record):
                log_entry = inner_self.format(record)

                if record.levelno >= logging.ERROR:
                    self._send_log(f"ERROR {log_entry}")
                elif record.levelno >= logging.WARNING:
                    self._send_log(f"WARN {log_entry}")
                else:
                    self._send_log(f"INFO {log_entry}")

        handler = LoggingHandler()
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.DEBUG)


# ---------------- USAGE ----------------
# from ai_log_analyzer_sdk import LogAnalyzerSDK
# sdk = LogAnalyzerSDK("http://127.0.0.1:5000", "YOUR_API_KEY")
# sdk.capture_message("App started")