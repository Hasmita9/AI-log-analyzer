import requests
import traceback
import logging


class LogAnalyzerSDK:
    def __init__(self, api_url, api_key):
        self.api_url = api_url
        self.api_key = api_key

    def _send_log(self, message):
        try:
            requests.post(
                f"{self.api_url}/api/ingest",
                json={"logs": [message]},
                headers={"X-API-Key": self.api_key}
            )
        except Exception as e:
            print("SDK failed to send log:", e)

    def capture_exception(self, error):
        error_message = f"ERROR {str(error)}\n{traceback.format_exc()}"
        self._send_log(error_message)

    def capture_message(self, message):
        log_message = f"INFO {message}"
        self._send_log(log_message)

    def setup_auto_capture(self):
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