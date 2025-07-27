"""
External Log Handlers for AICleaner v3
Phase 1C: Logging System Enhancement

This module provides external log handlers for integration with external
logging systems including syslog, remote logging, webhook notifications,
and third-party log aggregation services.

Key Features:
- Syslog integration (local and remote)
- Webhook log notifications
- HTTP/HTTPS log streaming
- MQTT log publishing
- Elasticsearch integration
- Slack/Discord notifications
- Email alerts
- Custom external endpoints
"""

import asyncio
import json
import logging.handlers
import smtplib
import socket
import ssl
import time
import urllib.parse
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, Union
import aiohttp
import paho.mqtt.client as mqtt
from dataclasses import dataclass

from .enhanced_logging import LogHandler, LogEntry, LogFilter, LogLevel, LogCategory


@dataclass
class ExternalEndpoint:
    """External logging endpoint configuration"""
    name: str
    endpoint_type: str  # syslog, webhook, http, mqtt, email, slack, discord
    url: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None
    ssl_enabled: bool = True
    timeout: int = 30
    retry_attempts: int = 3
    batch_size: int = 1
    metadata: Dict[str, Any] = None


class SyslogHandler(LogHandler):
    """Syslog handler for local and remote syslog"""
    
    FACILITY_MAP = {
        'kernel': 0, 'user': 1, 'mail': 2, 'daemon': 3,
        'auth': 4, 'syslog': 5, 'lpr': 6, 'news': 7,
        'uucp': 8, 'cron': 9, 'authpriv': 10, 'ftp': 11,
        'local0': 16, 'local1': 17, 'local2': 18, 'local3': 19,
        'local4': 20, 'local5': 21, 'local6': 22, 'local7': 23
    }
    
    PRIORITY_MAP = {
        LogLevel.TRACE: 7,      # debug
        LogLevel.DEBUG: 7,      # debug
        LogLevel.INFO: 6,       # info
        LogLevel.WARNING: 4,    # warning
        LogLevel.ERROR: 3,      # error
        LogLevel.CRITICAL: 2,   # critical
        LogLevel.SECURITY: 3,   # error
        LogLevel.AUDIT: 6       # info
    }
    
    def __init__(self, name: str, host: str = 'localhost', port: int = 514,
                 facility: str = 'user', protocol: str = 'udp',
                 log_filter: LogFilter = None):
        super().__init__(name, log_filter)
        self.host = host
        self.port = port
        self.facility = self.FACILITY_MAP.get(facility, 1)
        self.protocol = protocol.lower()
        self.socket = None
        
        self._setup_socket()
    
    def _setup_socket(self):
        """Setup syslog socket"""
        try:
            if self.protocol == 'udp':
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            elif self.protocol == 'tcp':
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((self.host, self.port))
            else:
                raise ValueError(f"Unsupported protocol: {self.protocol}")
        except Exception as e:
            print(f"Error setting up syslog socket: {e}")
            self.socket = None
    
    async def handle_log(self, entry: LogEntry) -> bool:
        """Handle log entry to syslog"""
        try:
            if not self.should_process(entry) or not self.socket:
                self.stats["messages_filtered"] += 1
                return False
            
            # Format syslog message
            priority = self.facility * 8 + self.PRIORITY_MAP.get(entry.level, 6)
            timestamp = entry.timestamp.strftime('%b %d %H:%M:%S')
            hostname = socket.gethostname()
            tag = f"aicleaner[{entry.process_id}]"
            message = self._format_message(entry)
            
            syslog_msg = f"<{priority}>{timestamp} {hostname} {tag}: {message}"
            
            # Send to syslog
            if self.protocol == 'udp':
                self.socket.sendto(syslog_msg.encode('utf-8'), (self.host, self.port))
            elif self.protocol == 'tcp':
                self.socket.send(syslog_msg.encode('utf-8') + b'\n')
            
            self.stats["messages_processed"] += 1
            self.stats["last_message_time"] = datetime.now()
            return True
            
        except Exception as e:
            self.stats["errors"] += 1
            print(f"Error in SyslogHandler: {e}")
            
            # Try to reconnect
            self._setup_socket()
            return False
    
    def _format_message(self, entry: LogEntry) -> str:
        """Format message for syslog"""
        parts = [
            f"[{entry.level.name}]",
            f"[{entry.context.component or 'system'}]",
            entry.message
        ]
        
        if entry.context.correlation_id:
            parts.append(f"(ID: {entry.context.correlation_id[:8]})")
        
        return " ".join(parts)


class WebhookHandler(LogHandler):
    """Webhook handler for HTTP/HTTPS log notifications"""
    
    def __init__(self, name: str, webhook_url: str, 
                 headers: Optional[Dict[str, str]] = None,
                 batch_size: int = 1, timeout: int = 30,
                 log_filter: LogFilter = None):
        super().__init__(name, log_filter)
        self.webhook_url = webhook_url
        self.headers = headers or {'Content-Type': 'application/json'}
        self.batch_size = batch_size
        self.timeout = timeout
        self.batch_buffer = []
        self.last_flush = datetime.now()
        self.flush_interval = 60  # seconds
    
    async def handle_log(self, entry: LogEntry) -> bool:
        """Handle log entry via webhook"""
        try:
            if not self.should_process(entry):
                self.stats["messages_filtered"] += 1
                return False
            
            # Add to batch buffer
            self.batch_buffer.append(self._format_entry(entry))
            
            # Send batch if full or timeout reached
            if (len(self.batch_buffer) >= self.batch_size or
                (datetime.now() - self.last_flush).seconds > self.flush_interval):
                await self._send_batch()
            
            return True
            
        except Exception as e:
            self.stats["errors"] += 1
            print(f"Error in WebhookHandler: {e}")
            return False
    
    def _format_entry(self, entry: LogEntry) -> Dict[str, Any]:
        """Format log entry for webhook"""
        return {
            "timestamp": entry.timestamp.isoformat(),
            "level": entry.level.name,
            "message": entry.message,
            "component": entry.context.component,
            "operation": entry.context.operation,
            "correlation_id": entry.context.correlation_id,
            "category": entry.context.category.value,
            "origin": entry.context.origin.value,
            "metadata": entry.context.metadata,
            "performance_metrics": entry.performance_metrics,
            "security_context": entry.security_context
        }
    
    async def _send_batch(self):
        """Send batch of log entries"""
        if not self.batch_buffer:
            return
        
        try:
            payload = {
                "service": "aicleaner",
                "timestamp": datetime.now().isoformat(),
                "logs": self.batch_buffer
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers=self.headers
                ) as response:
                    if response.status < 400:
                        self.stats["messages_processed"] += len(self.batch_buffer)
                    else:
                        self.stats["errors"] += 1
                        print(f"Webhook error: {response.status} - {await response.text()}")
            
            self.batch_buffer.clear()
            self.last_flush = datetime.now()
            
        except Exception as e:
            self.stats["errors"] += 1
            print(f"Error sending webhook batch: {e}")


class MQTTLogHandler(LogHandler):
    """MQTT handler for publishing logs to MQTT brokers"""
    
    def __init__(self, name: str, broker_host: str, broker_port: int = 1883,
                 topic_prefix: str = "aicleaner/logs", username: Optional[str] = None,
                 password: Optional[str] = None, use_ssl: bool = False,
                 log_filter: LogFilter = None):
        super().__init__(name, log_filter)
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.topic_prefix = topic_prefix
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        
        self.client = mqtt.Client()
        self.connected = False
        
        self._setup_mqtt()
    
    def _setup_mqtt(self):
        """Setup MQTT client"""
        try:
            if self.username and self.password:
                self.client.username_pw_set(self.username, self.password)
            
            if self.use_ssl:
                self.client.tls_set()
            
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            
            self.client.connect_async(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            
        except Exception as e:
            print(f"Error setting up MQTT: {e}")
    
    def _on_connect(self, client, userdata, flags, rc):
        """MQTT connect callback"""
        if rc == 0:
            self.connected = True
        else:
            self.connected = False
            print(f"MQTT connection failed: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """MQTT disconnect callback"""
        self.connected = False
    
    async def handle_log(self, entry: LogEntry) -> bool:
        """Handle log entry via MQTT"""
        try:
            if not self.should_process(entry) or not self.connected:
                self.stats["messages_filtered"] += 1
                return False
            
            # Determine topic
            topic = f"{self.topic_prefix}/{entry.level.name.lower()}"
            if entry.context.component:
                topic += f"/{entry.context.component}"
            
            # Format message
            message = self._format_entry(entry)
            
            # Publish
            result = self.client.publish(topic, json.dumps(message))
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.stats["messages_processed"] += 1
                self.stats["last_message_time"] = datetime.now()
                return True
            else:
                self.stats["errors"] += 1
                return False
            
        except Exception as e:
            self.stats["errors"] += 1
            print(f"Error in MQTTLogHandler: {e}")
            return False
    
    def _format_entry(self, entry: LogEntry) -> Dict[str, Any]:
        """Format log entry for MQTT"""
        return {
            "timestamp": entry.timestamp.isoformat(),
            "level": entry.level.name,
            "message": entry.message,
            "component": entry.context.component,
            "correlation_id": entry.context.correlation_id,
            "category": entry.context.category.value
        }


class SlackHandler(LogHandler):
    """Slack webhook handler for log notifications"""
    
    def __init__(self, name: str, webhook_url: str, channel: Optional[str] = None,
                 username: str = "AICleaner", min_level: LogLevel = LogLevel.ERROR,
                 log_filter: LogFilter = None):
        super().__init__(name, log_filter)
        self.webhook_url = webhook_url
        self.channel = channel
        self.username = username
        self.min_level = min_level
    
    async def handle_log(self, entry: LogEntry) -> bool:
        """Handle log entry to Slack"""
        try:
            if (not self.should_process(entry) or 
                entry.level.value < self.min_level.value):
                self.stats["messages_filtered"] += 1
                return False
            
            # Format Slack message
            message = self._format_slack_message(entry)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=message) as response:
                    if response.status == 200:
                        self.stats["messages_processed"] += 1
                        self.stats["last_message_time"] = datetime.now()
                        return True
                    else:
                        self.stats["errors"] += 1
                        return False
            
        except Exception as e:
            self.stats["errors"] += 1
            print(f"Error in SlackHandler: {e}")
            return False
    
    def _format_slack_message(self, entry: LogEntry) -> Dict[str, Any]:
        """Format message for Slack"""
        # Color coding based on log level
        color_map = {
            LogLevel.INFO: "good",
            LogLevel.WARNING: "warning", 
            LogLevel.ERROR: "danger",
            LogLevel.CRITICAL: "danger",
            LogLevel.SECURITY: "danger"
        }
        
        color = color_map.get(entry.level, "warning")
        
        # Create attachment
        attachment = {
            "color": color,
            "title": f"{entry.level.name} - {entry.context.component or 'System'}",
            "text": entry.message,
            "fields": [
                {
                    "title": "Timestamp",
                    "value": entry.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "short": True
                },
                {
                    "title": "Component", 
                    "value": entry.context.component or "Unknown",
                    "short": True
                }
            ],
            "footer": "AICleaner",
            "ts": int(entry.timestamp.timestamp())
        }
        
        if entry.context.correlation_id:
            attachment["fields"].append({
                "title": "Correlation ID",
                "value": entry.context.correlation_id[:8],
                "short": True
            })
        
        message = {
            "username": self.username,
            "attachments": [attachment]
        }
        
        if self.channel:
            message["channel"] = self.channel
        
        return message


class EmailHandler(LogHandler):
    """Email handler for critical log notifications"""
    
    def __init__(self, name: str, smtp_host: str, smtp_port: int = 587,
                 username: str = None, password: str = None,
                 from_email: str = None, to_emails: List[str] = None,
                 use_tls: bool = True, min_level: LogLevel = LogLevel.CRITICAL,
                 log_filter: LogFilter = None):
        super().__init__(name, log_filter)
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email or username
        self.to_emails = to_emails or []
        self.use_tls = use_tls
        self.min_level = min_level
    
    async def handle_log(self, entry: LogEntry) -> bool:
        """Handle log entry via email"""
        try:
            if (not self.should_process(entry) or 
                entry.level.value < self.min_level.value or
                not self.to_emails):
                self.stats["messages_filtered"] += 1
                return False
            
            # Create email
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            msg['Subject'] = f"AICleaner {entry.level.name}: {entry.context.component or 'System'}"
            
            # Create email body
            body = self._format_email_body(entry)
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            await self._send_email(msg)
            
            self.stats["messages_processed"] += 1
            self.stats["last_message_time"] = datetime.now()
            return True
            
        except Exception as e:
            self.stats["errors"] += 1
            print(f"Error in EmailHandler: {e}")
            return False
    
    def _format_email_body(self, entry: LogEntry) -> str:
        """Format email body"""
        return f"""
        <html>
        <body>
            <h2>AICleaner Log Alert</h2>
            <table border="1" cellpadding="5">
                <tr><td><strong>Level:</strong></td><td>{entry.level.name}</td></tr>
                <tr><td><strong>Timestamp:</strong></td><td>{entry.timestamp}</td></tr>
                <tr><td><strong>Component:</strong></td><td>{entry.context.component or 'Unknown'}</td></tr>
                <tr><td><strong>Operation:</strong></td><td>{entry.context.operation or 'Unknown'}</td></tr>
                <tr><td><strong>Message:</strong></td><td>{entry.message}</td></tr>
                <tr><td><strong>Correlation ID:</strong></td><td>{entry.context.correlation_id}</td></tr>
            </table>
            
            {self._format_additional_context(entry)}
        </body>
        </html>
        """
    
    def _format_additional_context(self, entry: LogEntry) -> str:
        """Format additional context information"""
        sections = []
        
        if entry.exception_info:
            sections.append(f"""
            <h3>Exception Information</h3>
            <pre>{entry.exception_info}</pre>
            """)
        
        if entry.performance_metrics:
            sections.append(f"""
            <h3>Performance Metrics</h3>
            <pre>{json.dumps(entry.performance_metrics, indent=2)}</pre>
            """)
        
        if entry.security_context:
            sections.append(f"""
            <h3>Security Context</h3>
            <pre>{json.dumps(entry.security_context, indent=2)}</pre>
            """)
        
        return "".join(sections)
    
    async def _send_email(self, msg: MIMEMultipart):
        """Send email message"""
        server = smtplib.SMTP(self.smtp_host, self.smtp_port)
        
        try:
            if self.use_tls:
                server.starttls()
            
            if self.username and self.password:
                server.login(self.username, self.password)
            
            server.send_message(msg)
            
        finally:
            server.quit()


class ElasticsearchHandler(LogHandler):
    """Elasticsearch handler for log indexing"""
    
    def __init__(self, name: str, es_url: str, index_prefix: str = "aicleaner-logs",
                 username: Optional[str] = None, password: Optional[str] = None,
                 batch_size: int = 100, log_filter: LogFilter = None):
        super().__init__(name, log_filter)
        self.es_url = es_url.rstrip('/')
        self.index_prefix = index_prefix
        self.username = username
        self.password = password
        self.batch_size = batch_size
        self.batch_buffer = []
        self.last_flush = datetime.now()
        self.flush_interval = 30  # seconds
        
        # Setup auth headers
        self.headers = {'Content-Type': 'application/json'}
        if username and password:
            import base64
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            self.headers['Authorization'] = f'Basic {credentials}'
    
    async def handle_log(self, entry: LogEntry) -> bool:
        """Handle log entry to Elasticsearch"""
        try:
            if not self.should_process(entry):
                self.stats["messages_filtered"] += 1
                return False
            
            # Add to batch buffer
            self.batch_buffer.append(self._format_entry(entry))
            
            # Send batch if full or timeout reached
            if (len(self.batch_buffer) >= self.batch_size or
                (datetime.now() - self.last_flush).seconds > self.flush_interval):
                await self._send_batch()
            
            return True
            
        except Exception as e:
            self.stats["errors"] += 1
            print(f"Error in ElasticsearchHandler: {e}")
            return False
    
    def _format_entry(self, entry: LogEntry) -> Dict[str, Any]:
        """Format log entry for Elasticsearch"""
        return {
            "@timestamp": entry.timestamp.isoformat(),
            "level": entry.level.name,
            "message": entry.message,
            "component": entry.context.component,
            "operation": entry.context.operation,
            "correlation_id": entry.context.correlation_id,
            "session_id": entry.context.session_id,
            "user_id": entry.context.user_id,
            "category": entry.context.category.value,
            "origin": entry.context.origin.value,
            "tags": list(entry.context.tags),
            "metadata": entry.context.metadata,
            "logger_name": entry.logger_name,
            "module": entry.module,
            "function": entry.function,
            "line_number": entry.line_number,
            "thread_name": entry.thread_name,
            "process_id": entry.process_id,
            "exception_info": entry.exception_info,
            "performance_metrics": entry.performance_metrics,
            "security_context": entry.security_context
        }
    
    async def _send_batch(self):
        """Send batch to Elasticsearch"""
        if not self.batch_buffer:
            return
        
        try:
            # Create index name with date
            index_name = f"{self.index_prefix}-{datetime.now().strftime('%Y.%m.%d')}"
            
            # Create bulk request
            bulk_body = []
            for entry in self.batch_buffer:
                # Index action
                bulk_body.append(json.dumps({"index": {"_index": index_name}}))
                # Document
                bulk_body.append(json.dumps(entry))
            
            bulk_data = "\n".join(bulk_body) + "\n"
            
            # Send to Elasticsearch
            url = f"{self.es_url}/_bulk"
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    data=bulk_data,
                    headers=self.headers
                ) as response:
                    if response.status < 400:
                        self.stats["messages_processed"] += len(self.batch_buffer)
                    else:
                        self.stats["errors"] += 1
                        print(f"Elasticsearch error: {response.status}")
            
            self.batch_buffer.clear()
            self.last_flush = datetime.now()
            
        except Exception as e:
            self.stats["errors"] += 1
            print(f"Error sending to Elasticsearch: {e}")


class ExternalLogManager:
    """Manager for external log handlers"""
    
    def __init__(self):
        self.handlers: Dict[str, LogHandler] = {}
        self.endpoints: Dict[str, ExternalEndpoint] = {}
    
    def add_endpoint(self, endpoint: ExternalEndpoint):
        """Add external logging endpoint"""
        self.endpoints[endpoint.name] = endpoint
        
        # Create appropriate handler
        handler = self._create_handler(endpoint)
        if handler:
            self.handlers[endpoint.name] = handler
    
    def _create_handler(self, endpoint: ExternalEndpoint) -> Optional[LogHandler]:
        """Create handler for endpoint"""
        try:
            if endpoint.endpoint_type == "syslog":
                return SyslogHandler(
                    endpoint.name,
                    host=endpoint.host or 'localhost',
                    port=endpoint.port or 514
                )
            
            elif endpoint.endpoint_type == "webhook":
                headers = {}
                if endpoint.api_key:
                    headers['Authorization'] = f'Bearer {endpoint.api_key}'
                return WebhookHandler(
                    endpoint.name,
                    endpoint.url,
                    headers=headers,
                    batch_size=endpoint.batch_size
                )
            
            elif endpoint.endpoint_type == "mqtt":
                return MQTTLogHandler(
                    endpoint.name,
                    endpoint.host,
                    port=endpoint.port or 1883,
                    username=endpoint.username,
                    password=endpoint.password,
                    use_ssl=endpoint.ssl_enabled
                )
            
            elif endpoint.endpoint_type == "slack":
                return SlackHandler(
                    endpoint.name,
                    endpoint.url
                )
            
            elif endpoint.endpoint_type == "email":
                return EmailHandler(
                    endpoint.name,
                    endpoint.host,
                    port=endpoint.port or 587,
                    username=endpoint.username,
                    password=endpoint.password,
                    to_emails=endpoint.metadata.get('recipients', []) if endpoint.metadata else []
                )
            
            elif endpoint.endpoint_type == "elasticsearch":
                return ElasticsearchHandler(
                    endpoint.name,
                    endpoint.url,
                    username=endpoint.username,
                    password=endpoint.password,
                    batch_size=endpoint.batch_size
                )
            
            return None
            
        except Exception as e:
            print(f"Error creating handler for {endpoint.name}: {e}")
            return None
    
    def get_handler(self, name: str) -> Optional[LogHandler]:
        """Get handler by name"""
        return self.handlers.get(name)
    
    def remove_handler(self, name: str):
        """Remove handler"""
        self.handlers.pop(name, None)
        self.endpoints.pop(name, None)
    
    def list_handlers(self) -> List[str]:
        """List all handler names"""
        return list(self.handlers.keys())
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all external handlers"""
        stats = {}
        for name, handler in self.handlers.items():
            stats[name] = handler.stats.copy()
        return stats


# Global external log manager
_external_log_manager: Optional[ExternalLogManager] = None


def get_external_log_manager() -> ExternalLogManager:
    """Get global external log manager"""
    global _external_log_manager
    if _external_log_manager is None:
        _external_log_manager = ExternalLogManager()
    return _external_log_manager